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
