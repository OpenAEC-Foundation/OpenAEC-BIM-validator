"""Output formatters for IFC validation results.

This package provides formatters for different output formats:
- console: Rich-formatted console output (default)
- json: JSON output for programmatic consumption
- html: HTML report for human-readable reports
"""

# Console formatter (Rich-based output)
from ifc_validator.formatters.console import (
    format_console,
    format_console_to_string,
)

# JSON formatter
from ifc_validator.formatters.json import (
    format_json,
    format_json_compact,
    format_json_to_file,
    print_json,
)

# HTML formatter
from ifc_validator.formatters.html import (
    format_html,
    format_html_from_ids,
    format_html_from_ids_to_file,
    format_html_to_file,
    print_html,
)

__all__ = [
    # Console
    "format_console",
    "format_console_to_string",
    # JSON
    "format_json",
    "format_json_compact",
    "format_json_to_file",
    "print_json",
    # HTML
    "format_html",
    "format_html_from_ids",
    "format_html_from_ids_to_file",
    "format_html_to_file",
    "print_html",
]
