"""
Pydantic data models for IDS validation results.

This module contains the data structures for capturing IDS validation outcomes
at multiple levels: overall validation, per-specification, per-requirement,
and per-element. These models enable structured JSON serialization for
downstream features including UI display, report generation, and BCF export.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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


class ElementResult(BaseModel):
    """Validation result for a single IFC element.

    Captures the validation outcome for a specific IFC element,
    including its identification information and any failure messages.
    The global_id field enables linking to 3D viewer element highlighting.
    """

    global_id: Optional[str] = Field(
        None, description="IFC GlobalId (GUID) for 3D viewer linking"
    )
    element_type: str = Field(
        ..., description="IFC element type (e.g., IfcWall, IfcDoor)"
    )
    element_name: Optional[str] = Field(None, description="Element name from IFC")
    status: ValidationStatus = Field(..., description="Validation outcome")
    messages: list[str] = Field(
        default_factory=list, description="Validation failure messages"
    )
