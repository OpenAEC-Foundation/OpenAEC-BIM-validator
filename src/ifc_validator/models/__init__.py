"""Pydantic result models for IFC-IDS validation.

Re-exports all model classes for convenient access:
    from ifc_validator.models import ValidationResult
"""

from ifc_validator.models.results import (
    EntityFailure,
    SpecificationResult,
    ValidationResult,
)

__all__ = [
    "EntityFailure",
    "SpecificationResult",
    "ValidationResult",
]
