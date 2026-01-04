"""
IDS Validator Module

This module validates IFC files against IDS (Information Delivery Specification)
requirements using the ifctester library and returns structured validation results.

The module provides:
- Structured data models for validation results (dataclasses)
- Core validation function to run IDS checks against IFC models
- IDSValidator class for consistent API with other server modules

Usage:
    from server.ids_validator import IDSValidator, validate_ifc_against_ids
    from pathlib import Path

    # Using the function directly
    report = validate_ifc_against_ids(
        ifc_path=Path("model.ifc"),
        ids_path=Path("spec.ids")
    )
    print(f"Pass rate: {report.pass_rate_percent}%")

    # Using the class-based interface
    validator = IDSValidator()
    report = validator.validate(Path("model.ifc"), Path("spec.ids"))

Run as module for testing: python -m server.ids_validator
"""

# Standard library imports
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Third-party imports
import ifcopenshell
from ifctester import ids


@dataclass
class EntityFailure:
    """
    Details about a single entity that failed validation.

    This dataclass represents an IFC entity that did not meet the requirements
    specified in an IDS specification. It captures identifying information
    about the failed entity for reporting purposes.

    Attributes:
        entity_id: The IFC entity instance ID (from entity.id())
        entity_type: The IFC entity type/class name (from entity.is_a())
        entity_name: The Name attribute of the entity, if present
        global_id: The GlobalId (GUID) of the entity, if present
    """

    entity_id: int
    entity_type: str
    entity_name: Optional[str]
    global_id: Optional[str]


@dataclass
class SpecificationResult:
    """
    Validation result for a single IDS specification.

    This dataclass represents the validation outcome of a single specification
    within an IDS file when validated against an IFC model. It includes
    aggregate statistics and a list of failed entities for debugging.

    Attributes:
        name: The name/identifier of the IDS specification
        description: Optional description of what the specification checks
        passed: Whether all applicable entities passed this specification
        applicable_count: Number of IFC entities this specification applies to
        passed_count: Number of entities that passed the specification
        failed_count: Number of entities that failed the specification
        failures: List of EntityFailure objects with details about each failure
    """

    name: str
    description: Optional[str]
    passed: bool
    applicable_count: int
    passed_count: int
    failed_count: int
    failures: list[EntityFailure]


@dataclass
class ValidationReport:
    """
    Complete validation report for an IFC model against an IDS specification.

    This dataclass represents the full validation outcome including metadata
    about both files, aggregate statistics, timing metrics, and detailed
    results for each specification. It follows the pattern from ifc_processor.py
    with success/error fields for consistent error handling.

    Attributes:
        timestamp: ISO format timestamp when validation was performed
        ifc_file: Name/path of the IFC file that was validated
        ifc_schema: IFC schema version (e.g., 'IFC4X3', 'IFC2X3')
        ifc_entity_count: Total number of entities in the IFC model
        ids_file: Name/path of the IDS specification file used
        ids_title: Title from the IDS file metadata, if present
        validation_time_seconds: Time taken to run validation in seconds
        total_specifications: Total number of specifications in the IDS file
        passed_specifications: Number of specifications that passed
        failed_specifications: Number of specifications that failed
        pass_rate_percent: Percentage of specifications that passed (0-100)
        specifications: List of SpecificationResult objects with detailed results
        success: Whether the validation completed successfully (not pass/fail)
        error: Error message if validation failed to complete, None otherwise
    """

    timestamp: str
    ifc_file: str
    ifc_schema: str
    ifc_entity_count: int
    ids_file: str
    ids_title: Optional[str]
    validation_time_seconds: float
    total_specifications: int
    passed_specifications: int
    failed_specifications: int
    pass_rate_percent: float
    specifications: list[SpecificationResult]
    success: bool
    error: Optional[str]