"""Validation utilities for IFC and IDS files.

This module provides file validation functions including:
- File existence checks
- Extension validation for IFC (.ifc, .ifcxml, .ifczip) and IDS (.ids) files
- Memory preflight checks using psutil with 10x file size heuristic
- IFC-IDS validation workflow using IfcOpenShell and IfcTester

Usage:
    from ifc_validator.validator import (
        validate_ifc_file,
        validate_ids_file,
        check_memory_available,
        validate,
    )

    # Validate and load IFC file
    ifc_path = validate_ifc_file("/path/to/model.ifc")

    # Check memory before loading
    if not check_memory_available(ifc_path):
        raise MemoryError("Insufficient memory")

    # Run IFC-IDS validation
    result = validate(ifc_path, ids_path)
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import ifcopenshell
import psutil
from ifctester import ids


# Valid file extensions
VALID_IFC_EXTENSIONS = {".ifc", ".ifcxml", ".ifczip"}
VALID_IDS_EXTENSIONS = {".ids"}

# Memory expansion factor for IFC files when loaded into memory
IFC_MEMORY_EXPANSION_FACTOR = 10


def validate_file_exists(file_path: Union[str, Path], file_type: str = "File") -> Path:
    """Validate that a file exists and return a Path object.

    Args:
        file_path: Path to the file (string or Path object)
        file_type: Description of file type for error messages (e.g., "IFC", "IDS")

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If the file does not exist
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"{file_type} file not found: {file_path}")

    if not path.is_file():
        raise FileNotFoundError(f"{file_type} path is not a file: {file_path}")

    return path


def validate_ifc_extension(file_path: Union[str, Path]) -> Path:
    """Validate that a file has a valid IFC extension.

    Valid extensions: .ifc, .ifcxml, .ifczip

    Args:
        file_path: Path to the file

    Returns:
        Path object for the validated file

    Raises:
        ValueError: If the file has an invalid extension
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension not in VALID_IFC_EXTENSIONS:
        valid_exts = ", ".join(sorted(VALID_IFC_EXTENSIONS))
        raise ValueError(
            f"Invalid IFC file extension: '{extension}'. "
            f"Valid extensions are: {valid_exts}"
        )

    return path


def validate_ids_extension(file_path: Union[str, Path]) -> Path:
    """Validate that a file has a valid IDS extension.

    Valid extensions: .ids

    Args:
        file_path: Path to the file

    Returns:
        Path object for the validated file

    Raises:
        ValueError: If the file has an invalid extension
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension not in VALID_IDS_EXTENSIONS:
        valid_exts = ", ".join(sorted(VALID_IDS_EXTENSIONS))
        raise ValueError(
            f"Invalid IDS file extension: '{extension}'. "
            f"Valid extensions are: {valid_exts}"
        )

    return path


def check_memory_available(file_path: Union[str, Path]) -> bool:
    """Check if sufficient memory is available to load an IFC file.

    IFC files expand approximately 10x when loaded into memory.
    This function checks if available system memory exceeds the
    estimated memory requirement.

    Args:
        file_path: Path to the IFC file

    Returns:
        True if sufficient memory is available, False otherwise
    """
    path = Path(file_path)

    if not path.exists():
        return False

    file_size = path.stat().st_size
    available_memory = psutil.virtual_memory().available
    required_memory = file_size * IFC_MEMORY_EXPANSION_FACTOR

    return available_memory > required_memory


def get_memory_info(file_path: Union[str, Path]) -> dict:
    """Get detailed memory information for loading a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file_size, available_memory, required_memory,
        and is_sufficient fields
    """
    path = Path(file_path)

    if not path.exists():
        return {
            "file_size": 0,
            "available_memory": psutil.virtual_memory().available,
            "required_memory": 0,
            "is_sufficient": False,
            "error": "File does not exist",
        }

    file_size = path.stat().st_size
    available_memory = psutil.virtual_memory().available
    required_memory = file_size * IFC_MEMORY_EXPANSION_FACTOR

    return {
        "file_size": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "available_memory": available_memory,
        "available_memory_mb": round(available_memory / (1024 * 1024), 2),
        "required_memory": required_memory,
        "required_memory_mb": round(required_memory / (1024 * 1024), 2),
        "is_sufficient": available_memory > required_memory,
    }


def validate_ifc_file(file_path: Union[str, Path]) -> Path:
    """Validate an IFC file: check existence, extension, and memory.

    Performs validation in order:
    1. Check file exists
    2. Validate extension (.ifc, .ifcxml, .ifczip)
    3. Check memory availability

    Args:
        file_path: Path to the IFC file

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file has invalid extension
        MemoryError: If insufficient memory available
    """
    # Check existence
    path = validate_file_exists(file_path, "IFC")

    # Check extension
    validate_ifc_extension(path)

    # Check memory
    if not check_memory_available(path):
        memory_info = get_memory_info(path)
        raise MemoryError(
            f"Insufficient memory to load IFC file. "
            f"File size: {memory_info['file_size_mb']:.1f} MB, "
            f"Required: ~{memory_info['required_memory_mb']:.1f} MB, "
            f"Available: {memory_info['available_memory_mb']:.1f} MB"
        )

    return path


def validate_ids_file(file_path: Union[str, Path]) -> Path:
    """Validate an IDS file: check existence and extension.

    Performs validation in order:
    1. Check file exists
    2. Validate extension (.ids)

    Args:
        file_path: Path to the IDS file

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file has invalid extension
    """
    # Check existence
    path = validate_file_exists(file_path, "IDS")

    # Check extension
    validate_ids_extension(path)

    return path


# -----------------------------------------------------------------------------
# Validation Result Dataclasses
# -----------------------------------------------------------------------------


@dataclass
class EntityFailure:
    """Details about a failed entity from IDS validation.

    Attributes:
        entity_id: The IFC entity ID
        entity_type: The IFC entity type (e.g., "IfcWall")
        entity_name: The Name attribute if present
        global_id: The GlobalId attribute if present
    """

    entity_id: int
    entity_type: str
    entity_name: Optional[str]
    global_id: Optional[str]


@dataclass
class SpecificationResult:
    """Validation result for a single IDS specification.

    Attributes:
        name: The specification name
        description: The specification description (may be None)
        passed: Whether the specification passed validation
        applicable_count: Number of entities the specification applied to
        passed_count: Number of entities that passed
        failed_count: Number of entities that failed
        failures: List of EntityFailure details for failed entities
    """

    name: str
    description: Optional[str]
    passed: bool
    applicable_count: int
    passed_count: int
    failed_count: int
    failures: list = field(default_factory=list)


@dataclass
class ValidationResult:
    """Complete validation result from IFC-IDS validation.

    Attributes:
        timestamp: ISO format timestamp of validation
        ifc_file: Name of the IFC file
        ifc_schema: IFC schema version (e.g., "IFC4")
        ifc_entity_count: Total entities in the IFC file
        ids_file: Name of the IDS file
        ids_title: Title from IDS metadata (may be None)
        validation_time_seconds: Time taken for validation
        total_specifications: Total number of specifications checked
        passed_specifications: Number of specifications that passed
        failed_specifications: Number of specifications that failed
        pass_rate_percent: Percentage of specifications that passed
        specifications: List of SpecificationResult objects
        overall_pass: True if all specifications passed
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
    specifications: list = field(default_factory=list)
    overall_pass: bool = True


# -----------------------------------------------------------------------------
# IFC-IDS Validation Functions
# -----------------------------------------------------------------------------


def _extract_entity_failure(entity) -> EntityFailure:
    """Extract failure details from an IFC entity.

    Args:
        entity: An IFC entity object from IfcOpenShell

    Returns:
        EntityFailure with extracted details
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
        # Fallback for entities that don't support standard methods
        return EntityFailure(
            entity_id=0,
            entity_type="Unknown",
            entity_name=None,
            global_id=None,
        )


def load_ifc_model(file_path: Union[str, Path]) -> ifcopenshell.file:
    """Load an IFC model from file.

    Args:
        file_path: Path to the IFC file

    Returns:
        Loaded IFC model

    Raises:
        RuntimeError: If the file cannot be parsed
    """
    try:
        return ifcopenshell.open(str(file_path))
    except Exception as e:
        raise RuntimeError(f"Failed to parse IFC file: {e}") from e


def load_ids_specification(file_path: Union[str, Path]):
    """Load an IDS specification from file.

    Args:
        file_path: Path to the IDS file

    Returns:
        Loaded IDS specification object

    Raises:
        RuntimeError: If the file cannot be parsed
    """
    try:
        return ids.open(str(file_path))
    except Exception as e:
        raise RuntimeError(f"Failed to parse IDS file: {e}") from e


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
        ifc_path: Path to the IFC model file
        ids_path: Path to the IDS specification file

    Returns:
        ValidationResult with complete validation results

    Raises:
        FileNotFoundError: If IFC or IDS file not found
        ValueError: If files have invalid extensions
        MemoryError: If insufficient memory to load IFC file
        RuntimeError: If parsing fails
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

    # Extract IDS title - check for None on metadata fields
    ids_title = None
    if hasattr(ids_file, "info") and ids_file.info is not None:
        ids_title = getattr(ids_file.info, "title", None)

    # Run validation - this modifies ids_file.specifications in-place
    start_time = time.time()
    ids_file.validate(ifc_model)
    validation_time = time.time() - start_time

    # Collect specification results
    spec_results = []
    passed_specs = 0
    failed_specs = 0

    for spec in ids_file.specifications:
        # Get spec name - check for None
        spec_name = spec.name if spec.name is not None else "Unnamed Specification"

        # Get passed status
        passed = spec.status if hasattr(spec, "status") else True

        # Get description - may be None
        description = getattr(spec, "description", None)

        # Get applicable entities - ALWAYS wrap in list() for safe iteration
        applicable_entities = []
        if hasattr(spec, "applicable_entities") and spec.applicable_entities is not None:
            applicable_entities = list(spec.applicable_entities)
        applicable_count = len(applicable_entities)

        # Get failed entities - CRITICAL: use failed_entities, NOT failed_elements
        # ALWAYS wrap in list() for safe iteration
        failed_entities = []
        if hasattr(spec, "failed_entities") and spec.failed_entities is not None:
            failed_entities = list(spec.failed_entities)
        failed_count = len(failed_entities)

        # Calculate passed count
        passed_count = applicable_count - failed_count if applicable_count > 0 else 0

        # Extract failure details
        failures = [_extract_entity_failure(entity) for entity in failed_entities]

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

    # Determine overall pass/fail
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
