"""
Validation Proof-of-Concept Script.

This script demonstrates the complete IFC-IDS validation workflow using ifctester.
It can be used as a reference implementation or run directly for validation.

Usage:
    # Run with default files
    python research/validation_poc.py

    # Run with custom files
    python research/validation_poc.py --ifc path/to/model.ifc --ids path/to/spec.ids

    # Generate JSON output
    python research/validation_poc.py --output results.json
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class EntityFailure:
    """Details about a failed entity."""

    entity_id: int
    entity_type: str
    entity_name: Optional[str]
    global_id: Optional[str]


@dataclass
class SpecificationResult:
    """Validation result for a single specification."""

    name: str
    description: Optional[str]
    passed: bool
    applicable_count: int
    passed_count: int
    failed_count: int
    failures: list


@dataclass
class ValidationReport:
    """Complete validation report."""

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
    specifications: list


def extract_entity_failure(entity) -> EntityFailure:
    """Extract failure details from an IFC entity."""
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


def validate_ifc_against_ids(ifc_path: Path, ids_path: Path) -> ValidationReport:
    """
    Validate an IFC model against an IDS specification.

    Args:
        ifc_path: Path to the IFC model file
        ids_path: Path to the IDS specification file

    Returns:
        ValidationReport with complete validation results

    Raises:
        FileNotFoundError: If IFC or IDS file not found
        Exception: If validation fails
    """
    from ifctester import ids
    import ifcopenshell

    # Validate file existence
    if not ifc_path.exists():
        raise FileNotFoundError(f"IFC file not found: {ifc_path}")
    if not ids_path.exists():
        raise FileNotFoundError(f"IDS file not found: {ids_path}")

    # Load IFC model
    ifc_model = ifcopenshell.open(str(ifc_path))
    ifc_schema = ifc_model.schema
    ifc_entity_count = sum(1 for _ in ifc_model)

    # Load IDS specification
    ids_file = ids.open(str(ids_path))
    ids_title = None
    if hasattr(ids_file, "info") and ids_file.info:
        ids_title = getattr(ids_file.info, "title", None)

    # Run validation
    start_time = time.time()
    ids_file.validate(ifc_model)
    validation_time = time.time() - start_time

    # Collect specification results
    spec_results = []
    passed_specs = 0
    failed_specs = 0

    for spec in ids_file.specifications:
        spec_name = spec.name
        passed = spec.status if hasattr(spec, "status") else True
        description = getattr(spec, "description", None)

        # Get applicable entities
        applicable_entities = []
        if hasattr(spec, "applicable_entities"):
            applicable_entities = list(spec.applicable_entities)
        applicable_count = len(applicable_entities)

        # Get failed entities - CRITICAL: use failed_entities, NOT failed_elements
        failed_entities = []
        if hasattr(spec, "failed_entities"):
            failed_entities = list(spec.failed_entities)
        failed_count = len(failed_entities)

        # Calculate passed count
        passed_count = applicable_count - failed_count if applicable_count > 0 else 0

        # Extract failure details
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

        if passed:
            passed_specs += 1
        else:
            failed_specs += 1

    # Calculate pass rate
    total_specs = len(ids_file.specifications)
    pass_rate = (passed_specs / total_specs * 100) if total_specs > 0 else 0.0

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
    )


def print_report(report: ValidationReport, verbose: bool = False):
    """Print validation report to console."""

    print("\n" + "=" * 70)
    print("VALIDATION REPORT")
    print("=" * 70)

    print(f"\nTimestamp: {report.timestamp}")
    print(f"\nIFC Model:")
    print(f"  File: {report.ifc_file}")
    print(f"  Schema: {report.ifc_schema}")
    print(f"  Entity Count: {report.ifc_entity_count:,}")

    print(f"\nIDS Specification:")
    print(f"  File: {report.ids_file}")
    if report.ids_title:
        print(f"  Title: {report.ids_title}")

    print(f"\nValidation:")
    print(f"  Time: {report.validation_time_seconds:.3f} seconds")
    print(f"  Specifications: {report.total_specifications}")
    print(f"  Passed: {report.passed_specifications}")
    print(f"  Failed: {report.failed_specifications}")
    print(f"  Pass Rate: {report.pass_rate_percent:.1f}%")

    print("\n" + "-" * 70)
    print("SPECIFICATION DETAILS")
    print("-" * 70)

    for i, spec in enumerate(report.specifications, 1):
        status = "[PASS]" if spec.passed else "[FAIL]"
        print(f"\n{i}. {status} {spec.name}")

        if spec.description:
            desc = spec.description[:60] + "..." if len(spec.description) > 60 else spec.description
            print(f"   Description: {desc}")

        if spec.applicable_count > 0:
            print(f"   Applicable: {spec.applicable_count}, Passed: {spec.passed_count}, Failed: {spec.failed_count}")

        if verbose and not spec.passed and spec.failures:
            print("   Failed entities:")
            max_show = 3
            for failure in spec.failures[:max_show]:
                name_str = f" '{failure.entity_name}'" if failure.entity_name else ""
                print(f"     - #{failure.entity_id} {failure.entity_type}{name_str}")
            if len(spec.failures) > max_show:
                print(f"     ... and {len(spec.failures) - max_show} more")

    print("\n" + "=" * 70)


def report_to_dict(report: ValidationReport) -> dict:
    """Convert report to dictionary for JSON serialization."""
    data = {
        "timestamp": report.timestamp,
        "ifc_file": report.ifc_file,
        "ifc_schema": report.ifc_schema,
        "ifc_entity_count": report.ifc_entity_count,
        "ids_file": report.ids_file,
        "ids_title": report.ids_title,
        "validation_time_seconds": report.validation_time_seconds,
        "total_specifications": report.total_specifications,
        "passed_specifications": report.passed_specifications,
        "failed_specifications": report.failed_specifications,
        "pass_rate_percent": report.pass_rate_percent,
        "specifications": [],
    }

    for spec in report.specifications:
        spec_data = {
            "name": spec.name,
            "description": spec.description,
            "passed": spec.passed,
            "applicable_count": spec.applicable_count,
            "passed_count": spec.passed_count,
            "failed_count": spec.failed_count,
            "failures": [asdict(f) for f in spec.failures],
        }
        data["specifications"].append(spec_data)

    return data


def get_default_paths() -> tuple:
    """Get default IFC and IDS file paths."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Default IDS file
    ids_path = project_root / "ids-bestanden" / "NL_BIM_Basis_ILS_v2.ids"

    # Default IFC file
    ifc_path = project_root / "test" / "2786_CLT_model.ifc"

    return ifc_path, ids_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate IFC model against IDS specification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validation_poc.py
  python validation_poc.py --ifc model.ifc --ids spec.ids
  python validation_poc.py --output results.json
  python validation_poc.py --verbose
        """,
    )
    parser.add_argument(
        "--ifc",
        type=Path,
        help="Path to IFC model file (default: test/2786_CLT_model.ifc)",
    )
    parser.add_argument(
        "--ids",
        type=Path,
        help="Path to IDS specification file (default: ids-bestanden/NL_BIM_Basis_ILS_v2.ids)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file for validation results",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed failure information",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only show summary, no specification details",
    )

    args = parser.parse_args()

    # Get file paths
    default_ifc, default_ids = get_default_paths()
    ifc_path = args.ifc if args.ifc else default_ifc
    ids_path = args.ids if args.ids else default_ids

    # Run validation
    print("=" * 70)
    print("IFC-IDS VALIDATION POC")
    print("=" * 70)
    print(f"\nIFC: {ifc_path}")
    print(f"IDS: {ids_path}")
    print("\nRunning validation...")

    try:
        report = validate_ifc_against_ids(ifc_path, ids_path)
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Validation failed - {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Print results
    if not args.quiet:
        print_report(report, verbose=args.verbose)
    else:
        print(f"\nValidation completed in {report.validation_time_seconds:.3f}s")
        print(f"Result: {report.passed_specifications}/{report.total_specifications} passed ({report.pass_rate_percent:.1f}%)")

    # Write JSON output if requested
    if args.output:
        report_dict = report_to_dict(report)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        print(f"\nResults written to: {args.output}")

    # Exit with appropriate code
    if report.failed_specifications == 0:
        print("\nAll specifications passed!")
        sys.exit(0)
    else:
        print(f"\n{report.failed_specifications} specification(s) failed.")
        sys.exit(0)  # Still exit 0 as validation ran successfully


if __name__ == "__main__":
    main()
