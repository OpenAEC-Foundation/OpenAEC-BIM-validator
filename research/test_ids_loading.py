"""
Test script to verify IDS file loading and inspect structure.

This script validates that the NL_BIM_Basis_ILS.ids file loads correctly
using ifctester and documents its structure (specifications, requirements).

Run: python research/test_ids_loading.py
"""

from pathlib import Path
import sys


def get_ids_path() -> Path:
    """Get path to the NL_BIM_Basis_ILS IDS file."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Check both potential locations
    ids_paths = [
        project_root / "ids-bestanden" / "NL_BIM_Basis_ILS_v2.ids",
        project_root / "claude-code" / "fixtures" / "NL_BIM_Basis_ILS.ids",
    ]

    for path in ids_paths:
        if path.exists():
            return path

    return ids_paths[0]  # Return default path for error message


def test_ids_loading():
    """Test that NL_BIM_Basis_ILS.ids loads correctly and inspect its structure."""

    print("=" * 70)
    print("IDS File Loading Test - NL_BIM_Basis_ILS")
    print("=" * 70)

    # Step 1: Verify ifctester import
    print("\n[1/4] Verifying ifctester import...")
    try:
        from ifctester import ids
    except ImportError as e:
        print(f"FAILED: Could not import ifctester - {e}")
        print("Install with: pip install ifctester")
        return False
    print("OK: ifctester imported successfully")

    # Step 2: Locate IDS file
    print("\n[2/4] Locating IDS file...")
    ids_path = get_ids_path()

    if not ids_path.exists():
        print(f"FAILED: IDS file not found at {ids_path}")
        return False
    print(f"OK: Found IDS file at {ids_path}")

    # Step 3: Load IDS file
    print("\n[3/4] Loading IDS file...")
    try:
        ids_file = ids.open(str(ids_path))
    except Exception as e:
        print(f"FAILED: Could not load IDS file - {e}")
        return False
    print("OK: IDS file loaded successfully")

    # Step 4: Inspect IDS structure
    print("\n[4/4] Inspecting IDS structure...")
    print("-" * 70)

    # IDS Info
    print("\n## IDS Metadata")
    if hasattr(ids_file, 'info') and ids_file.info:
        info = ids_file.info
        if hasattr(info, 'title') and info.title:
            print(f"Title: {info.title}")
        if hasattr(info, 'description') and info.description:
            print(f"Description: {info.description}")
        if hasattr(info, 'version') and info.version:
            print(f"Version: {info.version}")
        if hasattr(info, 'author') and info.author:
            print(f"Author: {info.author}")
        if hasattr(info, 'date') and info.date:
            print(f"Date: {info.date}")
        if hasattr(info, 'purpose') and info.purpose:
            print(f"Purpose: {info.purpose}")
    else:
        print("No metadata available")

    # Specifications
    print(f"\n## Specifications ({len(ids_file.specifications)} total)")
    print("-" * 70)

    for i, spec in enumerate(ids_file.specifications, 1):
        print(f"\n### Specification {i}: {spec.name}")

        # Description
        if hasattr(spec, 'description') and spec.description:
            print(f"    Description: {spec.description}")

        # Instructions
        if hasattr(spec, 'instructions') and spec.instructions:
            print(f"    Instructions: {spec.instructions}")

        # IFC Version
        if hasattr(spec, 'ifcVersion') and spec.ifcVersion:
            print(f"    IFC Version: {spec.ifcVersion}")

        # Applicability (what entities does this apply to)
        if hasattr(spec, 'applicability') and spec.applicability:
            print(f"    Applicability:")
            for facet in spec.applicability:
                facet_type = type(facet).__name__
                print(f"      - {facet_type}")
                _print_facet_details(facet, indent=8)

        # Requirements (what must be true)
        if hasattr(spec, 'requirements') and spec.requirements:
            print(f"    Requirements ({len(spec.requirements)}):")
            for j, req in enumerate(spec.requirements, 1):
                req_type = type(req).__name__
                print(f"      [{j}] {req_type}")
                _print_facet_details(req, indent=10)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"IDS File: {ids_path.name}")
    print(f"Total Specifications: {len(ids_file.specifications)}")

    # Count requirement types
    req_types = {}
    for spec in ids_file.specifications:
        if hasattr(spec, 'requirements'):
            for req in spec.requirements:
                req_type = type(req).__name__
                req_types[req_type] = req_types.get(req_type, 0) + 1

    if req_types:
        print("\nRequirement Types Used:")
        for req_type, count in sorted(req_types.items()):
            print(f"  - {req_type}: {count}")

    print("\n" + "=" * 70)
    print("TEST PASSED: IDS file loaded and structure inspected successfully")
    print("=" * 70)

    return True


def _print_facet_details(facet, indent: int = 4):
    """Print details of a facet (requirement or applicability)."""
    prefix = " " * indent
    facet_type = type(facet).__name__

    # Entity facet
    if hasattr(facet, 'name') and hasattr(facet, 'predefinedType'):
        if facet.name:
            print(f"{prefix}Entity: {_get_restriction_value(facet.name)}")
        if facet.predefinedType:
            print(f"{prefix}PredefinedType: {_get_restriction_value(facet.predefinedType)}")

    # Property facet
    if facet_type == 'Property':
        if hasattr(facet, 'propertySet'):
            print(f"{prefix}PropertySet: {_get_restriction_value(facet.propertySet)}")
        if hasattr(facet, 'baseName'):
            print(f"{prefix}Property: {_get_restriction_value(facet.baseName)}")
        if hasattr(facet, 'value'):
            print(f"{prefix}Value: {_get_restriction_value(facet.value)}")

    # Attribute facet
    if facet_type == 'Attribute':
        if hasattr(facet, 'name'):
            print(f"{prefix}Attribute: {_get_restriction_value(facet.name)}")
        if hasattr(facet, 'value'):
            print(f"{prefix}Value: {_get_restriction_value(facet.value)}")

    # Classification facet
    if facet_type == 'Classification':
        if hasattr(facet, 'system'):
            print(f"{prefix}System: {_get_restriction_value(facet.system)}")
        if hasattr(facet, 'value'):
            print(f"{prefix}Value: {_get_restriction_value(facet.value)}")

    # Material facet
    if facet_type == 'Material':
        if hasattr(facet, 'value'):
            print(f"{prefix}Value: {_get_restriction_value(facet.value)}")

    # PartOf facet
    if facet_type == 'PartOf':
        if hasattr(facet, 'name'):
            print(f"{prefix}Relation: {_get_restriction_value(facet.name)}")


def _get_restriction_value(restriction) -> str:
    """Extract a readable value from a restriction."""
    if restriction is None:
        return "None"

    # Simple value
    if isinstance(restriction, str):
        return restriction

    # Restriction object
    if hasattr(restriction, 'value'):
        return str(restriction.value)

    # SimpleValue
    if hasattr(restriction, '__str__'):
        value_str = str(restriction)
        if value_str and value_str != "None":
            return value_str

    return str(type(restriction).__name__)


def main():
    """Main entry point."""
    success = test_ids_loading()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
