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


def report_to_dict(report: ValidationReport) -> dict:
    """
    Convert a ValidationReport to a dictionary for JSON serialization.

    This function uses dataclasses.asdict to recursively convert the
    ValidationReport and all its nested dataclasses (SpecificationResult,
    EntityFailure) to a dictionary structure that can be directly
    serialized to JSON using json.dumps().

    Args:
        report: A ValidationReport dataclass instance containing validation
                results, specifications, and entity failures.

    Returns:
        dict: A dictionary representation of the report with all nested
              dataclasses converted to dicts. The structure is:
              {
                  "timestamp": str,
                  "ifc_file": str,
                  "ifc_schema": str,
                  "ifc_entity_count": int,
                  "ids_file": str,
                  "ids_title": str | None,
                  "validation_time_seconds": float,
                  "total_specifications": int,
                  "passed_specifications": int,
                  "failed_specifications": int,
                  "pass_rate_percent": float,
                  "specifications": [
                      {
                          "name": str,
                          "description": str | None,
                          "passed": bool,
                          "applicable_count": int,
                          "passed_count": int,
                          "failed_count": int,
                          "failures": [
                              {
                                  "entity_id": int,
                                  "entity_type": str,
                                  "entity_name": str | None,
                                  "global_id": str | None
                              },
                              ...
                          ]
                      },
                      ...
                  ],
                  "success": bool,
                  "error": str | None
              }

    Example:
        >>> report = validate_ifc_against_ids(ifc_path, ids_path)
        >>> report_dict = report_to_dict(report)
        >>> import json
        >>> json_str = json.dumps(report_dict, indent=2)
    """
    return asdict(report)


def extract_entity_failure(entity) -> EntityFailure:
    """
    Safely extract failure details from an IFC entity.

    This helper function extracts identifying information from an IFC entity
    that failed validation. It uses defensive programming with getattr for
    optional attributes and exception handling for robustness.

    Args:
        entity: An IFC entity object from ifcopenshell (typically from
                spec.failed_entities after validation)

    Returns:
        EntityFailure: A dataclass containing entity details:
            - entity_id: The IFC instance ID (from entity.id())
            - entity_type: The IFC type/class (from entity.is_a())
            - entity_name: The Name attribute if present, else None
            - global_id: The GlobalId (GUID) if present, else None

    Note:
        If any exception occurs during extraction (e.g., malformed entity),
        returns a fallback EntityFailure with entity_id=0 and entity_type="Unknown".
    """
    try:
        # Extract required fields using IFC entity methods
        entity_id = entity.id()
        entity_type = entity.is_a()

        # Extract optional attributes using getattr pattern
        # Not all IFC entities have Name or GlobalId attributes
        entity_name = getattr(entity, "Name", None)
        global_id = getattr(entity, "GlobalId", None)

        return EntityFailure(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            global_id=global_id,
        )
    except Exception:
        # Handle malformed entities or unexpected errors gracefully
        # Return a fallback entity that can still be serialized and reported
        return EntityFailure(
            entity_id=0,
            entity_type="Unknown",
            entity_name=None,
            global_id=None,
        )


def validate_ifc_against_ids(ifc_path: Path, ids_path: Path) -> ValidationReport:
    """
    Validate an IFC model against an IDS specification.

    This is the main validation function that loads both files, runs validation
    using ifctester, and extracts results into a structured ValidationReport.
    The function includes timing metrics and comprehensive error handling.

    Args:
        ifc_path: Path to the IFC model file (.ifc)
        ids_path: Path to the IDS specification file (.ids)

    Returns:
        ValidationReport: Complete validation results including:
            - Metadata about both files
            - Aggregate statistics (pass/fail counts, pass rate)
            - Detailed results for each specification
            - Timing metrics
            - success=True if validation completed successfully

    Raises:
        FileNotFoundError: If IFC or IDS file does not exist at the specified path.
            The exception message includes the path that was not found.

    Example:
        >>> from pathlib import Path
        >>> report = validate_ifc_against_ids(
        ...     ifc_path=Path("model.ifc"),
        ...     ids_path=Path("spec.ids")
        ... )
        >>> print(f"Pass rate: {report.pass_rate_percent}%")
        Pass rate: 75.0%
    """
    # Validate file existence before attempting to load
    if not ifc_path.exists():
        raise FileNotFoundError(f"IFC file not found: {ifc_path}")
    if not ids_path.exists():
        raise FileNotFoundError(f"IDS file not found: {ids_path}")

    try:
        # Load IFC model using ifcopenshell
        ifc_model = ifcopenshell.open(str(ifc_path))
        ifc_schema = ifc_model.schema
        # Count total entities in the model
        ifc_entity_count = sum(1 for _ in ifc_model)

        # Load IDS specification using ifctester
        ids_file = ids.open(str(ids_path))

        # Extract IDS title from metadata if available
        ids_title = None
        if hasattr(ids_file, "info") and ids_file.info:
            ids_title = getattr(ids_file.info, "title", None)

        # Run validation with timing
        # Note: validate() modifies ids_file in-place with results
        start_time = time.time()
        ids_file.validate(ifc_model)
        validation_time = time.time() - start_time

        # Collect specification results
        spec_results: list[SpecificationResult] = []
        passed_specs = 0
        failed_specs = 0

        for spec in ids_file.specifications:
            spec_name = spec.name
            # Get pass/fail status - spec.status is set after validation
            passed = spec.status if hasattr(spec, "status") else True
            description = getattr(spec, "description", None)

            # Get applicable entities (entities this spec applies to)
            applicable_entities = []
            if hasattr(spec, "applicable_entities"):
                applicable_entities = list(spec.applicable_entities)
            applicable_count = len(applicable_entities)

            # CRITICAL: Use failed_entities, NOT failed_elements (documented gotcha)
            # failed_elements is an incorrect attribute name that does not exist
            failed_entities = []
            if hasattr(spec, "failed_entities"):
                failed_entities = list(spec.failed_entities)
            failed_count = len(failed_entities)

            # Calculate passed count from applicable minus failed
            passed_count = applicable_count - failed_count if applicable_count > 0 else 0

            # Extract failure details for each failed entity
            failures = [extract_entity_failure(entity) for entity in failed_entities]

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

            # Track aggregate pass/fail counts
            if passed:
                passed_specs += 1
            else:
                failed_specs += 1

        # Calculate overall pass rate percentage
        total_specs = len(ids_file.specifications)
        pass_rate = (passed_specs / total_specs * 100) if total_specs > 0 else 0.0

        # Build successful validation report
        return ValidationReport(
            timestamp=datetime.now().isoformat(),
            ifc_file=ifc_path.name,
            ifc_schema=ifc_schema,
            ifc_entity_count=ifc_entity_count,
            ids_file=ids_path.name,
            ids_title=ids_title,
            validation_time_seconds=round(validation_time, 3),
            total_specifications=total_specs,
            passed_specifications=passed_specs,
            failed_specifications=failed_specs,
            pass_rate_percent=round(pass_rate, 1),
            specifications=spec_results,
            success=True,
            error=None,
        )

    except Exception as e:
        # Handle validation errors gracefully
        # Return a report with success=False and error details
        return ValidationReport(
            timestamp=datetime.now().isoformat(),
            ifc_file=ifc_path.name,
            ifc_schema="Unknown",
            ifc_entity_count=0,
            ids_file=ids_path.name,
            ids_title=None,
            validation_time_seconds=0.0,
            total_specifications=0,
            passed_specifications=0,
            failed_specifications=0,
            pass_rate_percent=0.0,
            specifications=[],
            success=False,
            error=str(e),
        )


class IDSValidator:
    """
    IDS Validator for validating IFC models against IDS specifications.

    This class provides a consistent interface for IDS validation, following
    the pattern established by IFCProcessor in the server module. It wraps
    the core validation function and provides module capability information.

    Usage:
        validator = IDSValidator()

        # Check capabilities
        caps = validator.get_capabilities()
        print(f"ifctester version: {caps['ifctester_version']}")

        # Validate an IFC model
        report = validator.validate(Path("model.ifc"), Path("spec.ids"))
        print(f"Pass rate: {report.pass_rate_percent}%")
    """

    def __init__(self) -> None:
        """
        Initialize the IDS validator.

        The validator is stateless and does not require any configuration.
        Each validation call is independent and returns a complete report.
        """
        pass

    def get_capabilities(self) -> dict:
        """
        Return available validation capabilities and module information.

        This method provides information about the validator module including
        library versions and supported features. Useful for debugging and
        for API endpoints that need to report module status.

        Returns:
            dict: A dictionary containing:
                - ifcopenshell_version: Version of ifcopenshell library
                - ifctester_version: Version of ifctester library (if available)
                - supported_ids_versions: List of supported IDS versions
                - validation_available: Always True for this module
        """
        # Get ifctester version if available
        ifctester_version = "unknown"
        try:
            import ifctester

            if hasattr(ifctester, "__version__"):
                ifctester_version = ifctester.__version__
            elif hasattr(ifctester, "version"):
                ifctester_version = ifctester.version
        except (ImportError, AttributeError):
            pass

        return {
            "ifcopenshell_version": ifcopenshell.version,
            "ifctester_version": ifctester_version,
            "supported_ids_versions": ["1.0"],
            "validation_available": True,
        }

    def validate(self, ifc_path: Path, ids_path: Path) -> ValidationReport:
        """
        Validate an IFC model against an IDS specification.

        This method wraps the validate_ifc_against_ids() function, providing
        a consistent class-based interface for validation operations.

        Args:
            ifc_path: Path to the IFC model file (.ifc)
            ids_path: Path to the IDS specification file (.ids)

        Returns:
            ValidationReport: Complete validation results including:
                - Metadata about both files
                - Aggregate statistics (pass/fail counts, pass rate)
                - Detailed results for each specification
                - Timing metrics
                - success=True if validation completed successfully

        Raises:
            FileNotFoundError: If IFC or IDS file does not exist at the specified path.
                The exception message includes the path that was not found.

        Example:
            >>> validator = IDSValidator()
            >>> report = validator.validate(Path("model.ifc"), Path("spec.ids"))
            >>> if report.success:
            ...     print(f"Pass rate: {report.pass_rate_percent}%")
            ... else:
            ...     print(f"Validation error: {report.error}")
        """
        return validate_ifc_against_ids(ifc_path, ids_path)