"""
Data models for IDS validation results.

This module exports Pydantic models for structured validation result data:
- ValidationResult: Top-level container for validation run
- SpecificationResult: Results for a single IDS specification
- RequirementResult: Results for a single requirement
- ElementResult: Validation outcome for a specific IFC element
- SeverityLevel: Enum for IDS severity levels
- ValidationStatus: Enum for validation outcome status
"""

from server.models.validation_results import (
    ElementResult,
    RequirementResult,
    SeverityLevel,
    SpecificationResult,
    ValidationResult,
    ValidationStatus,
)

__all__ = [
    "ValidationResult",
    "SpecificationResult",
    "RequirementResult",
    "ElementResult",
    "SeverityLevel",
    "ValidationStatus",
]
