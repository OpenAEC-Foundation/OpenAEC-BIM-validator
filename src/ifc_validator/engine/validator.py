"""Core IFC-IDS validation logic.

This module provides the ``validate()`` function that orchestrates
the complete IFC-IDS validation workflow: file checks, loading,
running validation, and collecting structured results.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Union

from ifc_validator.engine.file_utils import validate_ifc_file, validate_ids_file
from ifc_validator.engine.parser import load_ifc_model, load_ids_specification
from ifc_validator.models import (
    EntityFailure,
    SpecificationResult,
    ValidationResult,
)


def _extract_entity_failure(entity) -> EntityFailure:
    """Extract failure details from an IFC entity.

    Args:
        entity: An IFC entity object from IfcOpenShell.

    Returns:
        EntityFailure with extracted details.
    """
    try:
        entity_id = entity.id()
        entity_type = entity.is_a()
        entity_name = getattr(entity, "Name", None)
        global_id = getattr(entity, "GlobalId", None)

        return EntityFailure(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            global_id=global_id,
        )
    except Exception:
        return EntityFailure(
            entity_id=0,
            entity_type="Unknown",
            entity_name=None,
            global_id=None,
        )


def validate(
    ifc_path: Union[str, Path],
    ids_path: Union[str, Path],
) -> ValidationResult:
    """Validate an IFC model against an IDS specification.

    This function performs the complete IFC-IDS validation workflow:
    1. Validates input files (existence, extension, memory)
    2. Loads the IFC model using IfcOpenShell
    3. Loads the IDS specification using IfcTester
    4. Runs validation
    5. Collects and structures the results

    Args:
        ifc_path: Path to the IFC model file.
        ids_path: Path to the IDS specification file.

    Returns:
        ValidationResult with complete validation results.

    Raises:
        FileNotFoundError: If IFC or IDS file not found.
        ValueError: If files have invalid extensions.
        MemoryError: If insufficient memory to load IFC file.
        RuntimeError: If parsing fails.
    """
    # Validate input files
    ifc_validated_path = validate_ifc_file(ifc_path)
    ids_validated_path = validate_ids_file(ids_path)

    # Load IFC model
    ifc_model = load_ifc_model(ifc_validated_path)
    ifc_schema = ifc_model.schema
    ifc_entity_count = sum(1 for _ in ifc_model)

    # Load IDS specification
    ids_file = load_ids_specification(ids_validated_path)

    # Extract IDS title
    ids_title = None
    if hasattr(ids_file, "info") and ids_file.info is not None:
        ids_title = getattr(ids_file.info, "title", None)

    # Run validation — modifies ids_file.specifications in-place
    start_time = time.time()
    ids_file.validate(ifc_model)
    validation_time = time.time() - start_time

    # Collect specification results
    spec_results = []
    passed_specs = 0
    failed_specs = 0

    for spec in ids_file.specifications:
        spec_name = (
            spec.name if spec.name is not None else "Unnamed Specification"
        )
        passed = spec.status if hasattr(spec, "status") else True
        description = getattr(spec, "description", None)

        # ALWAYS wrap in list() for safe iteration
        applicable_entities = []
        if (
            hasattr(spec, "applicable_entities")
            and spec.applicable_entities is not None
        ):
            applicable_entities = list(spec.applicable_entities)
        applicable_count = len(applicable_entities)

        # CRITICAL: use failed_entities, NOT failed_elements
        failed_entities = []
        if (
            hasattr(spec, "failed_entities")
            and spec.failed_entities is not None
        ):
            failed_entities = list(spec.failed_entities)
        failed_count = len(failed_entities)

        passed_count = (
            applicable_count - failed_count if applicable_count > 0 else 0
        )

        failures = [
            _extract_entity_failure(entity) for entity in failed_entities
        ]

        spec_result = SpecificationResult(
            name=spec_name,
            description=description,
            passed=passed,
            applicable_count=applicable_count,
            passed_count=passed_count,
            failed_count=failed_count,
            failures=failures,
        )
        spec_results.append(spec_result)

        if passed:
            passed_specs += 1
        else:
            failed_specs += 1

    # Calculate pass rate
    total_specs = len(ids_file.specifications)
    pass_rate = (passed_specs / total_specs * 100) if total_specs > 0 else 0.0

    overall_pass = failed_specs == 0

    return ValidationResult(
        timestamp=datetime.now().isoformat(),
        ifc_file=ifc_validated_path.name,
        ifc_schema=ifc_schema,
        ifc_entity_count=ifc_entity_count,
        ids_file=ids_validated_path.name,
        ids_title=ids_title,
        validation_time_seconds=round(validation_time, 3),
        total_specifications=total_specs,
        passed_specifications=passed_specs,
        failed_specifications=failed_specs,
        pass_rate_percent=round(pass_rate, 1),
        specifications=spec_results,
        overall_pass=overall_pass,
    )
