#!/usr/bin/env python
"""
Comparison script for validation_poc.py vs ids_validator.py

This script runs both validators on the same files and compares results
to ensure they match exactly (pass/fail counts and specification names).

Usage:
    python test/compare_validators.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def compare_validators(ifc_path: Path, ids_path: Path, test_name: str) -> bool:
    """
    Run comparison between POC and module validators for given files.

    Returns True if all results match, False otherwise.
    """
    print(f"\n{'=' * 70}")
    print(f"TEST: {test_name}")
    print(f"{'=' * 70}")
    print(f"\nTest files:")
    print(f"  IFC: {ifc_path}")
    print(f"  IDS: {ids_path}")

    # Verify files exist
    if not ifc_path.exists():
        print(f"\nERROR: IFC file not found: {ifc_path}")
        return False
    if not ids_path.exists():
        print(f"\nERROR: IDS file not found: {ids_path}")
        return False

    # === Run POC validator ===
    print("\n" + "-" * 70)
    print("Running validation_poc.py...")
    print("-" * 70)

    # Import POC module
    sys.path.insert(0, str(project_root / "research"))
    from validation_poc import validate_ifc_against_ids as poc_validate

    poc_report = poc_validate(ifc_path, ids_path)

    print(f"  Total specifications: {poc_report.total_specifications}")
    print(f"  Passed: {poc_report.passed_specifications}")
    print(f"  Failed: {poc_report.failed_specifications}")
    print(f"  Pass rate: {poc_report.pass_rate_percent}%")

    # Extract POC spec details
    poc_specs = {}
    for spec in poc_report.specifications:
        poc_specs[spec.name] = {
            "passed": spec.passed,
            "applicable_count": spec.applicable_count,
            "passed_count": spec.passed_count,
            "failed_count": spec.failed_count,
        }

    # === Run module validator ===
    print("\n" + "-" * 70)
    print("Running server/ids_validator.py...")
    print("-" * 70)

    from server.ids_validator import validate_ifc_against_ids as module_validate

    module_report = module_validate(ifc_path, ids_path)

    print(f"  Total specifications: {module_report.total_specifications}")
    print(f"  Passed: {module_report.passed_specifications}")
    print(f"  Failed: {module_report.failed_specifications}")
    print(f"  Pass rate: {module_report.pass_rate_percent}%")

    # Extract module spec details
    module_specs = {}
    for spec in module_report.specifications:
        module_specs[spec.name] = {
            "passed": spec.passed,
            "applicable_count": spec.applicable_count,
            "passed_count": spec.passed_count,
            "failed_count": spec.failed_count,
        }

    # === Compare results ===
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)

    all_match = True

    # Compare aggregate counts
    print("\n1. Aggregate Counts:")

    if poc_report.total_specifications != module_report.total_specifications:
        print(f"   ❌ Total specifications: POC={poc_report.total_specifications}, Module={module_report.total_specifications}")
        all_match = False
    else:
        print(f"   ✓ Total specifications: {poc_report.total_specifications}")

    if poc_report.passed_specifications != module_report.passed_specifications:
        print(f"   ❌ Passed specifications: POC={poc_report.passed_specifications}, Module={module_report.passed_specifications}")
        all_match = False
    else:
        print(f"   ✓ Passed specifications: {poc_report.passed_specifications}")

    if poc_report.failed_specifications != module_report.failed_specifications:
        print(f"   ❌ Failed specifications: POC={poc_report.failed_specifications}, Module={module_report.failed_specifications}")
        all_match = False
    else:
        print(f"   ✓ Failed specifications: {poc_report.failed_specifications}")

    if poc_report.pass_rate_percent != module_report.pass_rate_percent:
        print(f"   ❌ Pass rate: POC={poc_report.pass_rate_percent}%, Module={module_report.pass_rate_percent}%")
        all_match = False
    else:
        print(f"   ✓ Pass rate: {poc_report.pass_rate_percent}%")

    # Compare specification names
    print("\n2. Specification Names:")
    poc_names = set(poc_specs.keys())
    module_names = set(module_specs.keys())

    if poc_names != module_names:
        missing_in_module = poc_names - module_names
        extra_in_module = module_names - poc_names

        if missing_in_module:
            print(f"   ❌ Missing in module: {missing_in_module}")
        if extra_in_module:
            print(f"   ❌ Extra in module: {extra_in_module}")
        all_match = False
    else:
        print(f"   ✓ All {len(poc_names)} specification names match")

    # Compare individual specification results
    print("\n3. Per-Specification Results:")

    for spec_name in sorted(poc_names & module_names):
        poc_spec = poc_specs[spec_name]
        module_spec = module_specs[spec_name]

        matches = True
        issues = []

        if poc_spec["passed"] != module_spec["passed"]:
            matches = False
            issues.append(f"passed: POC={poc_spec['passed']}, Module={module_spec['passed']}")

        if poc_spec["applicable_count"] != module_spec["applicable_count"]:
            matches = False
            issues.append(f"applicable: POC={poc_spec['applicable_count']}, Module={module_spec['applicable_count']}")

        if poc_spec["passed_count"] != module_spec["passed_count"]:
            matches = False
            issues.append(f"passed_count: POC={poc_spec['passed_count']}, Module={module_spec['passed_count']}")

        if poc_spec["failed_count"] != module_spec["failed_count"]:
            matches = False
            issues.append(f"failed_count: POC={poc_spec['failed_count']}, Module={module_spec['failed_count']}")

        if matches:
            status = "PASS" if poc_spec["passed"] else "FAIL"
            print(f"   ✓ [{status}] {spec_name}")
        else:
            all_match = False
            print(f"   ❌ {spec_name}: {', '.join(issues)}")

    # Final summary
    print("\n" + "-" * 70)
    if all_match:
        print(f"✓ {test_name}: ALL VALIDATIONS MATCH")
    else:
        print(f"❌ {test_name}: MISMATCH DETECTED")

    return all_match


def main():
    """Run comparison between POC and module validators for all test files."""
    print("=" * 70)
    print("VALIDATOR COMPARISON: validation_poc.py vs ids_validator.py")
    print("=" * 70)

    # Import validators once
    sys.path.insert(0, str(project_root / "research"))

    # Define test cases
    test_cases = [
        {
            "name": "Production Test (CLT Model + NL BIM Basis ILS)",
            "ifc": project_root / "test" / "2786_CLT_model.ifc",
            "ids": project_root / "ids-bestanden" / "NL_BIM_Basis_ILS_v2.ids",
        },
        {
            "name": "Sample Test (Wall Naming Convention)",
            "ifc": project_root / "test" / "fixtures" / "sample.ifc",
            "ids": project_root / "test" / "fixtures" / "sample.ids",
        },
        {
            "name": "Failing Sample Test",
            "ifc": project_root / "test" / "fixtures" / "sample-fail.ifc",
            "ids": project_root / "test" / "fixtures" / "sample.ids",
        },
    ]

    # Run all test cases
    results = []
    for test_case in test_cases:
        ifc_path = test_case["ifc"]
        ids_path = test_case["ids"]
        test_name = test_case["name"]

        # Skip if files don't exist
        if not ifc_path.exists() or not ids_path.exists():
            print(f"\nSkipping {test_name} - files not found")
            continue

        result = compare_validators(ifc_path, ids_path, test_name)
        results.append((test_name, result))

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    print("-" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - POC and Module produce identical results")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Check output above for details")
        sys.exit(1)


if __name__ == "__main__":
    main()
