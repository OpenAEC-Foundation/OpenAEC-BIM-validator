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


class RequirementResult(BaseModel):
    """Validation result for a single requirement within an IDS specification.

    Captures the validation outcome for a specific requirement,
    linking to all elements that were evaluated against it.
    Includes aggregate statistics for pass/fail counts.
    """

    requirement_description: str = Field(
        ..., description="Human-readable requirement description"
    )
    status: ValidationStatus = Field(
        ..., description="Overall requirement validation status"
    )
    total_elements: int = Field(..., description="Total elements evaluated")
    failed_elements: int = Field(
        ..., description="Number of elements that failed this requirement"
    )
    elements: list[ElementResult] = Field(
        default_factory=list, description="Per-element validation results"
    )


class SpecificationResult(BaseModel):
    """Validation result for a single IDS specification.

    Captures the validation outcome for a complete IDS specification,
    including severity level and aggregate statistics across all requirements.
    Contains nested RequirementResult objects for detailed requirement-level data.
    """

    specification_name: str = Field(
        ..., description="Name of the IDS specification"
    )
    severity: SeverityLevel = Field(
        ..., description="Severity level from IDS (error, warning, info)"
    )
    status: ValidationStatus = Field(
        ..., description="Overall specification validation status"
    )
    total_requirements: int = Field(
        ..., description="Total requirements in specification"
    )
    failed_requirements: int = Field(
        ..., description="Number of failed requirements"
    )
    requirements: list[RequirementResult] = Field(
        default_factory=list, description="Per-requirement validation results"
    )


class ValidationResult(BaseModel):
    """Top-level container for IDS validation run.

    Captures the complete validation outcome for an IFC file against an IDS
    specification file. Contains aggregate statistics and nested SpecificationResult
    objects for detailed per-specification data.
    """

    success: bool = Field(
        ..., description="Overall validation success (all specifications passed)"
    )
    total_specifications: int = Field(
        ..., description="Total specifications evaluated"
    )
    failed_specifications: int = Field(
        ..., description="Number of failed specifications"
    )
    total_elements_validated: int = Field(
        ..., description="Total IFC elements validated"
    )
    validation_timestamp: str = Field(
        ..., description="ISO 8601 timestamp of validation run"
    )
    specifications: list[SpecificationResult] = Field(
        default_factory=list, description="Per-specification validation results"
    )
    ifc_file_name: Optional[str] = Field(
        None, description="Name of validated IFC file"
    )
    ids_file_name: Optional[str] = Field(
        None, description="Name of IDS specification file"
    )
