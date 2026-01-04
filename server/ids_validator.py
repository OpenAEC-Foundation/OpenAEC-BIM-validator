"""
IDS Validator Module

This module validates IFC files against IDS (Information Delivery Specification)
requirements using the ifctester library and returns structured validation results.

The module provides:
- Structured data models for validation results (dataclasses)
- Core validation function to run IDS checks against IFC models
- IDSValidator class for consistent API with other server modules
"""

from dataclasses import dataclass
from typing import Optional


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