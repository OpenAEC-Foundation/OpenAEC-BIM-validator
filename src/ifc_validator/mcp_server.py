"""Zero-dependency MCP server exposing the validation engine.

Speaks the Model Context Protocol (newline-delimited JSON-RPC 2.0 over
stdio), so AI assistants such as Claude Desktop/Code can validate IFC
models against IDS specifications directly on the local machine. No
network, no API keys — model data never leaves the machine.

Run with::

    python -m ifc_validator.mcp_server

Claude Desktop config (claude_desktop_config.json)::

    {
      "mcpServers": {
        "ifc-validator": {
          "command": "python",
          "args": ["-m", "ifc_validator.mcp_server"]
        }
      }
    }

Design notes: stdout is sacred — only JSON-RPC messages are written to
it; all logging goes to stderr. Tool failures are reported as tool
results with ``isError: true`` (never protocol errors), so the client
model can read and act on the message.
"""

import io
import json
import sys
import traceback
from typing import Any, Optional

from ifc_validator.standards.resolver import (
    STANDARD_SHORTCUTS,
    get_bundled_ids,
    is_shortcut,
)

SERVER_NAME = "ifc-validator"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"

# JSON-RPC error codes
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
PARSE_ERROR = -32700


def _resolve_ids(ids: str) -> str:
    """Resolve an IDS argument: bundled-standard shortcut or file path."""
    if is_shortcut(ids):
        return str(get_bundled_ids(ids))
    return ids


def _summarize(result: Any, max_failures: int) -> dict[str, Any]:
    """Build a compact JSON summary of a ValidationResult for LLM use."""
    specs = []
    for spec in result.specifications:
        entry: dict[str, Any] = {
            "name": spec.name,
            "status": spec.status,
            "applicable_count": spec.applicable_count,
            "passed_count": spec.passed_count,
            "failed_count": spec.failed_count,
        }
        if spec.description:
            entry["description"] = spec.description
        if spec.not_checkable_reason:
            entry["not_checkable_reason"] = spec.not_checkable_reason
        if spec.failures:
            entry["failures"] = [
                {
                    "entity_type": f.entity_type,
                    "entity_name": f.entity_name,
                    "global_id": f.global_id,
                }
                for f in spec.failures[:max_failures]
            ]
            omitted = len(spec.failures) - max_failures
            if omitted > 0:
                entry["failures_omitted"] = omitted
        specs.append(entry)

    return {
        "ifc_file": result.ifc_file,
        "ifc_schema": result.ifc_schema,
        "ifc_entity_count": result.ifc_entity_count,
        "ids_file": result.ids_file,
        "ids_title": result.ids_title,
        "overall_pass": result.overall_pass,
        "total_specifications": result.total_specifications,
        "passed_specifications": result.passed_specifications,
        "failed_specifications": result.failed_specifications,
        "not_checkable_specifications": result.not_checkable_specifications,
        "pass_rate_percent": result.pass_rate_percent,
        "specifications": specs,
    }


def _tool_validate_ifc(args: dict[str, Any]) -> str:
    """Validate an IFC model against an IDS specification or standard."""
    ifc_path = args["ifc_path"]
    ids_path = _resolve_ids(args["ids"])
    max_failures = int(args.get("max_failures", 10))

    # Import lazily: IfcOpenShell is heavy and initialize/tools-list must
    # respond instantly
    from ifc_validator.engine.validator import validate

    result = validate(ifc_path, ids_path)
    return json.dumps(_summarize(result, max_failures), ensure_ascii=False)


def _tool_list_standards(_args: dict[str, Any]) -> str:
    """List the bundled IDS standards with their shortcuts."""
    descriptions = {
        "nl-bim": "NL BIM Basis ILS v2 — Dutch baseline BIM information "
        "level specification (12 specifications)",
        "rvb": "RVB BIM Norm v1.1 — Rijksvastgoedbedrijf Dutch Government "
        "Real Estate BIM norm (27 specifications)",
    }
    standards = [
        {
            "shortcut": shortcut,
            "filename": filename,
            "description": descriptions.get(shortcut, ""),
        }
        for shortcut, filename in STANDARD_SHORTCUTS.items()
    ]
    return json.dumps({"standards": standards}, ensure_ascii=False)


def _tool_export_report(args: dict[str, Any]) -> str:
    """Validate and write a full report to disk (html or json)."""
    ifc_path = args["ifc_path"]
    ids_path = _resolve_ids(args["ids"])
    fmt = args.get("format", "html")
    output_path = args["output_path"]

    from ifc_validator.engine.validator import validate

    result = validate(ifc_path, ids_path)

    if fmt == "html":
        from ifc_validator.formatters.html import format_html

        content = format_html(result)
    elif fmt == "json":
        content = result.model_dump_json(indent=2)
    else:
        raise ValueError(f"Unknown format: {fmt!r} (expected 'html' or 'json')")

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    return json.dumps(
        {
            "written": output_path,
            "format": fmt,
            "overall_pass": result.overall_pass,
            "failed_specifications": result.failed_specifications,
        },
        ensure_ascii=False,
    )


TOOLS: dict[str, dict[str, Any]] = {
    "validate_ifc": {
        "handler": _tool_validate_ifc,
        "description": (
            "Validate an IFC model against an IDS specification. Runs "
            "locally via IfcOpenShell/ifctester; the model never leaves "
            "the machine. Returns a JSON summary with per-specification "
            "status (passed/failed/not_checkable) and failing entities. "
            "Pass a bundled-standard shortcut ('nl-bim', 'rvb') or a path "
            "to an .ids file as 'ids'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ifc_path": {
                    "type": "string",
                    "description": "Absolute path to the .ifc file",
                },
                "ids": {
                    "type": "string",
                    "description": "Bundled standard shortcut (nl-bim, rvb)"
                    " or path to an .ids file",
                },
                "max_failures": {
                    "type": "integer",
                    "description": "Max failing entities per specification"
                    " in the summary (default 10)",
                },
            },
            "required": ["ifc_path", "ids"],
        },
    },
    "list_standards": {
        "handler": _tool_list_standards,
        "description": (
            "List the bundled IDS standards that can be passed as the "
            "'ids' argument of validate_ifc."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    "export_report": {
        "handler": _tool_export_report,
        "description": (
            "Validate an IFC model and write a full report to disk. "
            "Format 'html' gives a styled human-readable report, 'json' "
            "the complete machine-readable result."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ifc_path": {
                    "type": "string",
                    "description": "Absolute path to the .ifc file",
                },
                "ids": {
                    "type": "string",
                    "description": "Bundled standard shortcut (nl-bim, rvb)"
                    " or path to an .ids file",
                },
                "format": {
                    "type": "string",
                    "enum": ["html", "json"],
                    "description": "Report format (default html)",
                },
                "output_path": {
                    "type": "string",
                    "description": "Absolute path to write the report to",
                },
            },
            "required": ["ifc_path", "ids", "output_path"],
        },
    },
}


def _handle_request(method: str, params: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Dispatch a JSON-RPC request. Returns the result object.

    Raises _RpcError for protocol-level errors.
    """
    if method == "initialize":
        return {
            "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }

    if method == "ping":
        return {}

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": name,
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"],
                }
                for name, tool in TOOLS.items()
            ]
        }

    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        tool = TOOLS.get(name)
        if tool is None:
            return _tool_error(f"Unknown tool: {name!r}")
        try:
            text = tool["handler"](arguments)
        except KeyError as exc:
            return _tool_error(f"Missing required argument: {exc}")
        except Exception as exc:
            return _tool_error(f"{type(exc).__name__}: {exc}")
        return {"content": [{"type": "text", "text": text}], "isError": False}

    raise _RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")


def _tool_error(message: str) -> dict[str, Any]:
    """Tool-level error: reported in-band so the model can react to it."""
    return {"content": [{"type": "text", "text": message}], "isError": True}


class _RpcError(Exception):
    """JSON-RPC protocol error."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def main() -> None:
    """Run the stdio server loop until stdin closes."""
    # Belt and braces for Windows consoles: JSON-RPC must be clean UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    stdin: io.TextIOBase = sys.stdin
    for line in stdin:
        line = line.strip()
        if not line:
            continue

        response: Optional[dict[str, Any]] = None
        msg_id: Any = None
        try:
            msg = json.loads(line)
            msg_id = msg.get("id")
            method = msg.get("method", "")

            # Notifications (no id) get no response
            if msg_id is None:
                continue

            result = _handle_request(method, msg.get("params") or {})
            response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except _RpcError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": exc.code, "message": exc.message},
            }
        except json.JSONDecodeError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": PARSE_ERROR, "message": f"Parse error: {exc}"},
            }
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": "Internal error"},
            }

        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
