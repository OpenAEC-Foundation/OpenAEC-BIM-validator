"""
Pydantic data models for IDS validation results.

This module contains the data structures for capturing IDS validation outcomes
at multiple levels: overall validation, per-specification, per-requirement,
and per-element. These models enable structured JSON serialization for
downstream features including UI display, report generation, and BCF export.
"""

from enum import Enum


class SeverityLevel(str, Enum):
    """IDS severity levels.

    Represents the severity level defined in an IDS specification,
    indicating how critical a validation failure is.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationStatus(str, Enum):
    """Validation outcome status.

    Represents the possible outcomes of validating an element,
    requirement, or specification against IDS rules.
    """

    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
