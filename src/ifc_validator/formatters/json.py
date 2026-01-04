"""JSON output formatter for IFC validation results.

This module provides JSON-formatted output for validation results,
producing valid JSON with validation status, specifications, and
failure details using dataclass asdict() for serialization.

Usage:
    from ifc_validator.formatters.json import format_json, format_json_to_file
    from ifc_validator.validator import ValidationResult

    result: ValidationResult = validate(ifc_path, ids_path)

    # Get JSON string
    json_output = format_json(result)

    # Write to file
    format_json_to_file(result, "output.json")
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional, Union

from ifc_validator.validator import ValidationResult


def _result_to_dict(result: ValidationResult) -> dict[str, Any]:
    """Convert ValidationResult to a dictionary for JSON serialization.

    Uses dataclass asdict() for consistent serialization of all nested
    dataclasses (SpecificationResult, EntityFailure).

    Args:
        result: ValidationResult from IFC-IDS validation

    Returns:
        Dictionary representation ready for JSON serialization
    """
    return asdict(result)


def format_json(
    result: ValidationResult,
    indent: Optional[int] = 2,
    sort_keys: bool = False,
) -> str:
    """Format validation results as a JSON string.

    Produces valid, parseable JSON containing:
    - Validation metadata (timestamp, files, schema)
    - Summary statistics (total, passed, failed specs)
    - Detailed specification results with failures

    Args:
        result: ValidationResult from IFC-IDS validation
        indent: Number of spaces for indentation (None for compact, default 2)
        sort_keys: Whether to sort dictionary keys alphabetically

    Returns:
        JSON-formatted string

    Example output:
        {
          "timestamp": "2024-01-01T12:00:00",
          "ifc_file": "model.ifc",
          "ifc_schema": "IFC4",
          "overall_pass": false,
          "specifications": [...]
        }
    """
    data = _result_to_dict(result)
    return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)


def format_json_compact(result: ValidationResult) -> str:
    """Format validation results as compact JSON (no indentation).

    Useful for machine processing, logging, or when minimizing output size.

    Args:
        result: ValidationResult from IFC-IDS validation

    Returns:
        Compact JSON string with no whitespace
    """
    return format_json(result, indent=None)


def format_json_to_file(
    result: ValidationResult,
    output_path: Union[str, Path],
    indent: Optional[int] = 2,
    sort_keys: bool = False,
) -> Path:
    """Write validation results to a JSON file.

    Creates or overwrites the specified file with JSON-formatted
    validation results.

    Args:
        result: ValidationResult from IFC-IDS validation
        output_path: Path to the output JSON file
        indent: Number of spaces for indentation
        sort_keys: Whether to sort dictionary keys

    Returns:
        Path to the written file

    Raises:
        OSError: If the file cannot be written
    """
    path = Path(output_path)
    json_content = format_json(result, indent=indent, sort_keys=sort_keys)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(json_content, encoding="utf-8")
    return path


def print_json(
    result: ValidationResult,
    indent: Optional[int] = 2,
) -> None:
    """Print validation results as JSON to stdout.

    Convenience function for CLI output.

    Args:
        result: ValidationResult from IFC-IDS validation
        indent: Number of spaces for indentation
    """
    print(format_json(result, indent=indent))
