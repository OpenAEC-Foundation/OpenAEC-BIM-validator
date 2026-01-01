"""IFC Validator CLI module.

A command-line tool for validating IFC (Industry Foundation Classes) building
model files against IDS (Information Delivery Specification) rules.

Usage:
    ifc-validate path/to/model.ifc --ids path/to/rules.ids
    ifc-validate path/to/model.ifc --ids path/to/rules.ids --output json
    ifc-validate path/to/model.ifc --ids path/to/rules.ids --output html

Programmatic usage:
    from ifc_validator import validate, ValidationResult

    result = validate("model.ifc", "rules.ids")
    print(f"Overall pass: {result.overall_pass}")
"""

__version__ = "0.1.0"

# CLI app - entry point for ifc-validate command
from ifc_validator.cli import app

# Validation functions and result dataclasses
from ifc_validator.validator import (
    EntityFailure,
    SpecificationResult,
    ValidationResult,
    check_memory_available,
    get_memory_info,
    load_ifc_model,
    load_ids_specification,
    validate,
    validate_ifc_file,
    validate_ids_file,
)

# Formatters (re-exported from formatters package)
from ifc_validator.formatters import (
    format_console,
    format_console_to_string,
    format_html,
    format_html_to_file,
    format_json,
    format_json_compact,
    format_json_to_file,
    print_html,
    print_json,
)

__all__ = [
    # Version
    "__version__",
    # CLI
    "app",
    # Validation functions
    "validate",
    "validate_ifc_file",
    "validate_ids_file",
    "check_memory_available",
    "get_memory_info",
    "load_ifc_model",
    "load_ids_specification",
    # Result dataclasses
    "ValidationResult",
    "SpecificationResult",
    "EntityFailure",
    # Formatters
    "format_console",
    "format_console_to_string",
    "format_json",
    "format_json_compact",
    "format_json_to_file",
    "print_json",
    "format_html",
    "format_html_to_file",
    "print_html",
]
