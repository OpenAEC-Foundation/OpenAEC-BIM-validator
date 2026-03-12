"""Pydantic result models for IFC-IDS validation.

This module defines the structured result types used throughout the
validation pipeline. All models use Pydantic BaseModel for automatic
serialization, validation, and FastAPI compatibility.
"""

from typing import Optional

from pydantic import BaseModel, Field


class EntityFailure(BaseModel):
    """Details about a failed entity from IDS validation.

    Attributes:
        entity_id: The IFC entity ID.
        entity_type: The IFC entity type (e.g., "IfcWall").
        entity_name: The Name attribute if present.
        global_id: The GlobalId attribute if present.
    """

    entity_id: int
    entity_type: str
    entity_name: Optional[str] = None
    global_id: Optional[str] = None


class SpecificationResult(BaseModel):
    """Validation result for a single IDS specification.

    Attributes:
        name: The specification name.
        description: The specification description (may be None).
        passed: Whether the specification passed validation.
        applicable_count: Number of entities the specification applied to.
        passed_count: Number of entities that passed.
        failed_count: Number of entities that failed.
        failures: List of EntityFailure details for failed entities.
    """

    name: str
    description: Optional[str] = None
    passed: bool
    applicable_count: int
    passed_count: int
    failed_count: int
    failures: list[EntityFailure] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Complete validation result from IFC-IDS validation.

    Attributes:
        timestamp: ISO format timestamp of validation.
        ifc_file: Name of the IFC file.
        ifc_schema: IFC schema version (e.g., "IFC4").
        ifc_entity_count: Total entities in the IFC file.
        ids_file: Name of the IDS file.
        ids_title: Title from IDS metadata (may be None).
        validation_time_seconds: Time taken for validation.
        total_specifications: Total number of specifications checked.
        passed_specifications: Number of specifications that passed.
        failed_specifications: Number of specifications that failed.
        pass_rate_percent: Percentage of specifications that passed.
        specifications: List of SpecificationResult objects.
        overall_pass: True if all specifications passed.
    """

    timestamp: str
    ifc_file: str
    ifc_schema: str
    ifc_entity_count: int
    ids_file: str
    ids_title: Optional[str] = None
    validation_time_seconds: float
    total_specifications: int
    passed_specifications: int
    failed_specifications: int
    pass_rate_percent: float
    specifications: list[SpecificationResult] = Field(default_factory=list)
    overall_pass: bool = True
