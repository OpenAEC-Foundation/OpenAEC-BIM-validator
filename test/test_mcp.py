"""Verify the local MCP transport and validation/report tool contracts."""

import io
import json
from pathlib import Path

import pytest

from ifc_validator import __version__, mcp_server

FIXTURES = Path(__file__).parent / "fixtures"


def call_tool(name, arguments=None):
    return mcp_server._handle_request(
        "tools/call", {"name": name, "arguments": arguments or {}}
    )


def test_initialize_discovery_and_ping():
    initialized = mcp_server._handle_request("initialize", {})
    assert initialized["serverInfo"]["version"] == __version__
    assert mcp_server._handle_request("ping", {}) == {}
    discovered = mcp_server._handle_request("tools/list", {})["tools"]
    assert {item["name"] for item in discovered} == {
        "validate_ifc",
        "list_standards",
        "export_report",
    }
    response = call_tool("list_standards")
    assert response["isError"] is False
    standards = json.loads(response["content"][0]["text"])["standards"]
    assert {item["shortcut"] for item in standards} >= {"nl-bim", "rvb"}
    assert Path(mcp_server._resolve_ids("nl-bim")).is_file()


def test_validation_failure_summary_is_bounded():
    response = call_tool(
        "validate_ifc",
        {
            "ifc_path": str(FIXTURES / "sample-fail.ifc"),
            "ids": str(FIXTURES / "sample.ids"),
            "max_failures": 0,
        },
    )
    assert response["isError"] is False
    result = json.loads(response["content"][0]["text"])
    assert result["overall_pass"] is False
    failures = [s for s in result["specifications"] if s["failed_count"]]
    assert failures
    assert all(s["failures"] == [] and s["failures_omitted"] > 0 for s in failures)


@pytest.mark.parametrize("fmt", ["html", "json"])
def test_export_report_writes_requested_format(tmp_path, fmt):
    target = tmp_path / f"report.{fmt}"
    response = call_tool(
        "export_report",
        {
            "ifc_path": str(FIXTURES / "sample.ifc"),
            "ids": str(FIXTURES / "sample.ids"),
            "output_path": str(target),
            "format": fmt,
        },
    )
    assert response["isError"] is False
    written = json.loads(response["content"][0]["text"])
    assert written["written"] == str(target)
    content = target.read_text(encoding="utf-8")
    if fmt == "json":
        assert json.loads(content)["overall_pass"] is True
    else:
        assert "<html" in content.lower()


@pytest.mark.parametrize(
    "name,args",
    [
        ("missing_tool", {}),
        ("validate_ifc", {}),
        ("validate_ifc", {"ifc_path": "missing.ifc", "ids": "missing.ids"}),
    ],
)
def test_tool_errors_are_in_band(name, args):
    result = call_tool(name, args)
    assert result["isError"] is True
    assert result["content"][0]["text"]


def test_stdio_dispatch_keeps_notifications_silent_and_recovers_from_errors(
    monkeypatch,
):
    lines = [
        "",
        "{",
        json.dumps({"method": "notifications/initialized"}),
        json.dumps({"id": 1, "method": "unknown"}),
        json.dumps({"id": 2, "method": "ping"}),
    ]
    output = io.StringIO()
    monkeypatch.setattr(mcp_server.sys, "stdin", io.StringIO("\n".join(lines)))
    monkeypatch.setattr(mcp_server.sys, "stdout", output)
    mcp_server.main()
    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert len(responses) == 3
    assert responses[0]["error"]["code"] == -32700
    assert responses[1]["error"]["code"] == -32601
    assert responses[2] == {"jsonrpc": "2.0", "id": 2, "result": {}}
