"""
Comprehensive end-to-end validation test for ifctester.

This script runs ifctester validation of IFC files against IDS specifications
and captures detailed results including pass/fail status and failed entities.

Run: python research/test_validation.py
"""

from pathlib import Path
import sys
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    """Container for validation results of a single specification."""

    spec_name: str
    passed: bool
    description: Optional[str]
    applicable_count: int
    failed_count: int
    failed_entities: list


@dataclass
class ValidationSummary:
    """Container for overall validation summary."""

    ifc_file: str
    ids_file: str
    total_specs: int
    passed_specs: int
    failed_specs: int
    validation_time: float
    results: list


def get_project_paths() -> tuple:
    """Get paths to IDS and IFC files."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # IDS file paths
    ids_paths = [
        project_root / "ids-bestanden" / "NL_BIM_Basis_ILS_v2.ids",
        project_root / "ids-bestanden" / "NL_BIM_Basis_ILS.ids",
    ]

    # IFC test file
    ifc_path = project_root / "test" / "2786_CLT_model.ifc"

    # Find IDS file
    ids_path = None
    for path in ids_paths:
        if path.exists():
            ids_path = path
            break

    return ids_path, ifc_path


def format_entity_info(entity) -> str:
    """Format entity information for display."""
    try:
        entity_type = entity.is_a()
        entity_id = entity.id()
        entity_name = getattr(entity, "Name", None)

        if entity_name:
            return f"#{entity_id} {entity_type} '{entity_name}'"
        else:
            return f"#{entity_id} {entity_type}"
    except Exception:
        return str(entity)


def run_validation(ids_path: Path, ifc_path: Path) -> ValidationSummary:
    """
    Run ifctester validation and return detailed results.

    Args:
        ids_path: Path to the IDS specification file
        ifc_path: Path to the IFC model file

    Returns:
        ValidationSummary with all results
    """
    from ifctester import ids
    import ifcopenshell

    # Load IFC model
    ifc_model = ifcopenshell.open(str(ifc_path))

    # Load IDS specification
    ids_file = ids.open(str(ids_path))

    # Run validation and measure time
    start_time = time.time()
    ids_file.validate(ifc_model)
    validation_time = time.time() - start_time

    # Collect results
    results = []
    passed_count = 0
    failed_count = 0

    for spec in ids_file.specifications:
        # Get specification details
        spec_name = spec.name
        passed = spec.status if hasattr(spec, "status") else None
        description = getattr(spec, "description", None)

        # Get applicable entities count
        applicable_count = 0
        if hasattr(spec, "applicable_entities"):
            applicable_count = len(spec.applicable_entities)

        # Get failed entities - CRITICAL: use failed_entities, NOT failed_elements
        failed_entities_list = []
        if hasattr(spec, "failed_entities"):
            failed_entities_list = list(spec.failed_entities)

        result = ValidationResult(
            spec_name=spec_name,
            passed=passed if passed is not None else True,
            description=description,
            applicable_count=applicable_count,
            failed_count=len(failed_entities_list),
            failed_entities=failed_entities_list,
        )
        results.append(result)

        if result.passed:
            passed_count += 1
        else:
            failed_count += 1

    return ValidationSummary(
        ifc_file=ifc_path.name,
        ids_file=ids_path.name,
        total_specs=len(ids_file.specifications),
        passed_specs=passed_count,
        failed_specs=failed_count,
        validation_time=validation_time,
        results=results,
    )


def print_validation_results(summary: ValidationSummary, verbose: bool = True):
    """Print validation results in a structured format."""

    print("=" * 70)
    print("IFC VALIDATION RESULTS")
    print("=" * 70)

    print(f"\nIFC File: {summary.ifc_file}")
    print(f"IDS File: {summary.ids_file}")
    print(f"Validation Time: {summary.validation_time:.2f} seconds")

    print("\n" + "-" * 70)
    print("SPECIFICATION RESULTS")
    print("-" * 70)

    for i, result in enumerate(summary.results, 1):
        status = "PASSED" if result.passed else "FAILED"
        status_marker = "[PASS]" if result.passed else "[FAIL]"

        print(f"\n{i}. {status_marker} {result.spec_name}")

        if result.description:
            print(f"   Description: {result.description}")

        if result.applicable_count > 0:
            print(f"   Applicable entities: {result.applicable_count}")

        if not result.passed and result.failed_count > 0:
            print(f"   Failed entities: {result.failed_count}")

            if verbose and result.failed_entities:
                # Show up to 5 failed entities
                max_show = 5
                for j, entity in enumerate(result.failed_entities[:max_show]):
                    entity_info = format_entity_info(entity)
                    print(f"     - {entity_info}")

                if result.failed_count > max_show:
                    remaining = result.failed_count - max_show
                    print(f"     ... and {remaining} more")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Specifications: {summary.total_specs}")
    print(f"Passed: {summary.passed_specs}")
    print(f"Failed: {summary.failed_specs}")
    pass_rate = (
        (summary.passed_specs / summary.total_specs * 100)
        if summary.total_specs > 0
        else 0
    )
    print(f"Pass Rate: {pass_rate:.1f}%")


def test_validation() -> bool:
    """
    Run comprehensive validation test and capture detailed results.

    Returns:
        True if validation completes successfully (regardless of pass/fail results)
    """

    print("=" * 70)
    print("End-to-End Validation Test - ifctester")
    print("=" * 70)

    # Step 1: Verify imports
    print("\n[1/4] Verifying imports...")
    try:
        from ifctester import ids
        import ifcopenshell
    except ImportError as e:
        print(f"FAILED: Could not import required libraries - {e}")
        return False
    print(f"OK: ifcopenshell {ifcopenshell.version}, ifctester imported")

    # Step 2: Locate files
    print("\n[2/4] Locating IDS and IFC files...")
    ids_path, ifc_path = get_project_paths()

    if ids_path is None or not ids_path.exists():
        print(f"FAILED: IDS file not found")
        return False
    print(f"OK: IDS file found at {ids_path}")

    if not ifc_path.exists():
        print(f"FAILED: IFC file not found at {ifc_path}")
        return False
    print(f"OK: IFC file found at {ifc_path}")

    # Step 3: Run validation
    print("\n[3/4] Running validation...")
    try:
        summary = run_validation(ids_path, ifc_path)
    except Exception as e:
        print(f"FAILED: Validation error - {e}")
        import traceback

        traceback.print_exc()
        return False
    print(f"OK: Validation completed in {summary.validation_time:.2f}s")

    # Step 4: Display results
    print("\n[4/4] Validation Results")
    print("-" * 70)
    print_validation_results(summary, verbose=True)

    # Final status
    print("\n" + "=" * 70)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print("\nValidation ran without errors.")
    print(f"Result: {summary.passed_specs} passed, {summary.failed_specs} failed")

    return True


def main():
    """Main entry point."""
    success = test_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
