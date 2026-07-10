"""Tests for the stdio MCP server.

The server speaks newline-delimited JSON-RPC 2.0 over stdio and exposes
the validation engine as MCP tools. Tests drive a real subprocess, the
same way an MCP client (Claude Desktop/Code) would.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class McpClient:
    """Minimal newline-delimited JSON-RPC client over a subprocess."""

    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "ifc_validator.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self._id = 0

    def request(self, method, params=None):
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        assert line, f"no response for {method} (stderr: {self.proc.stderr.read()})"
        return json.loads(line)

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=10)


@pytest.fixture
def client():
    c = McpClient()
    resp = c.request(
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0"},
        },
    )
    assert "result" in resp, resp
    c.notify("notifications/initialized")
    yield c
    c.close()


def test_initialize_reports_server_info(client):
    # initialize already happened in the fixture; check via a fresh client
    c = McpClient()
    resp = c.request(
        "initialize",
        {"protocolVersion": "2025-06-18", "capabilities": {}},
    )
    result = resp["result"]
    assert result["serverInfo"]["name"] == "ifc-validator"
    assert "tools" in result["capabilities"]
    c.close()


def test_tools_list(client):
    resp = client.request("tools/list")
    tools = {t["name"]: t for t in resp["result"]["tools"]}
    assert "validate_ifc" in tools
    assert "list_standards" in tools
    assert "export_report" in tools
    for tool in tools.values():
        assert tool["inputSchema"]["type"] == "object"
        assert tool["description"]


def test_list_standards_tool(client):
    resp = client.request(
        "tools/call", {"name": "list_standards", "arguments": {}}
    )
    result = resp["result"]
    assert result.get("isError") is not True
    text = result["content"][0]["text"]
    data = json.loads(text)
    shortcuts = [s["shortcut"] for s in data["standards"]]
    assert "nl-bim" in shortcuts
    assert "rvb" in shortcuts


def test_validate_ifc_with_ids_path(client):
    resp = client.request(
        "tools/call",
        {
            "name": "validate_ifc",
            "arguments": {
                "ifc_path": str(FIXTURES / "sample.ifc"),
                "ids": str(FIXTURES / "sample.ids"),
            },
        },
    )
    result = resp["result"]
    assert result.get("isError") is not True, result
    data = json.loads(result["content"][0]["text"])
    assert data["ifc_file"] == "sample.ifc"
    assert data["total_specifications"] >= 1
    assert "overall_pass" in data
    assert isinstance(data["specifications"], list)
    spec = data["specifications"][0]
    assert {"name", "status", "applicable_count"} <= set(spec)


def test_validate_ifc_with_standard_shortcut(client):
    resp = client.request(
        "tools/call",
        {
            "name": "validate_ifc",
            "arguments": {
                "ifc_path": str(FIXTURES / "sample.ifc"),
                "ids": "nl-bim",
            },
        },
    )
    result = resp["result"]
    assert result.get("isError") is not True, result
    data = json.loads(result["content"][0]["text"])
    assert data["total_specifications"] >= 1


def test_validate_ifc_missing_file_is_tool_error(client):
    resp = client.request(
        "tools/call",
        {
            "name": "validate_ifc",
            "arguments": {"ifc_path": "does-not-exist.ifc", "ids": "nl-bim"},
        },
    )
    result = resp["result"]
    assert result["isError"] is True
    assert "does-not-exist.ifc" in result["content"][0]["text"]


def test_export_report_html(client, tmp_path):
    out = tmp_path / "report.html"
    resp = client.request(
        "tools/call",
        {
            "name": "export_report",
            "arguments": {
                "ifc_path": str(FIXTURES / "sample.ifc"),
                "ids": str(FIXTURES / "sample.ids"),
                "format": "html",
                "output_path": str(out),
            },
        },
    )
    result = resp["result"]
    assert result.get("isError") is not True, result
    assert out.exists()
    assert "<html" in out.read_text(encoding="utf-8").lower()


def test_unknown_method_returns_error(client):
    resp = client.request("bogus/method")
    assert resp["error"]["code"] == -32601


def test_unknown_tool_is_error(client):
    resp = client.request(
        "tools/call", {"name": "no_such_tool", "arguments": {}}
    )
    result = resp["result"]
    assert result["isError"] is True
