"""
Test script to verify IFC file loading and inspect model structure.

This script validates that IFC files load correctly using ifcopenshell
and documents the model structure (schema, entity types, counts).

Run: python research/test_ifc_loading.py
"""

from pathlib import Path
import sys
import time
from collections import Counter


def get_ifc_path() -> Path:
    """Get path to the test IFC file."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Primary test file
    ifc_path = project_root / "test" / "2786_CLT_model.ifc"

    return ifc_path


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def test_ifc_loading():
    """Test that IFC file loads correctly and inspect its structure."""

    print("=" * 70)
    print("IFC File Loading Test - ifcopenshell")
    print("=" * 70)

    # Step 1: Verify ifcopenshell import
    print("\n[1/5] Verifying ifcopenshell import...")
    try:
        import ifcopenshell
    except ImportError as e:
        print(f"FAILED: Could not import ifcopenshell - {e}")
        print("Install with: pip install ifcopenshell")
        return False
    print(f"OK: ifcopenshell {ifcopenshell.version} imported successfully")

    # Step 2: Locate IFC file
    print("\n[2/5] Locating IFC file...")
    ifc_path = get_ifc_path()

    if not ifc_path.exists():
        print(f"FAILED: IFC file not found at {ifc_path}")
        return False

    file_size = ifc_path.stat().st_size
    print(f"OK: Found IFC file at {ifc_path}")
    print(f"    File size: {format_file_size(file_size)}")

    # Step 3: Load IFC file
    print("\n[3/5] Loading IFC file...")
    start_time = time.time()
    try:
        ifc_model = ifcopenshell.open(str(ifc_path))
    except Exception as e:
        print(f"FAILED: Could not load IFC file - {e}")
        return False
    load_time = time.time() - start_time
    print(f"OK: IFC file loaded successfully in {load_time:.2f} seconds")

    # Step 4: Inspect IFC schema and basic info
    print("\n[4/5] Inspecting IFC schema and metadata...")
    print("-" * 70)

    print("\n## IFC Schema Information")
    print(f"Schema: {ifc_model.schema}")

    # Get header information if available
    if hasattr(ifc_model, 'header'):
        header = ifc_model.header
        print("\n## Header Information")
        if hasattr(header, 'file_description'):
            desc = header.file_description
            if hasattr(desc, 'description'):
                print(f"Description: {desc.description}")
            if hasattr(desc, 'implementation_level'):
                print(f"Implementation Level: {desc.implementation_level}")
        if hasattr(header, 'file_name'):
            fname = header.file_name
            if hasattr(fname, 'name'):
                print(f"File Name: {fname.name}")
            if hasattr(fname, 'time_stamp'):
                print(f"Time Stamp: {fname.time_stamp}")
            if hasattr(fname, 'author'):
                print(f"Author: {fname.author}")
            if hasattr(fname, 'organization'):
                print(f"Organization: {fname.organization}")
            if hasattr(fname, 'preprocessor_version'):
                print(f"Preprocessor: {fname.preprocessor_version}")
            if hasattr(fname, 'originating_system'):
                print(f"Originating System: {fname.originating_system}")
            if hasattr(fname, 'authorization'):
                print(f"Authorization: {fname.authorization}")

    # Step 5: Analyze model structure
    print("\n[5/5] Analyzing model structure...")
    print("-" * 70)

    # Count all entity types
    entity_types = Counter()
    for entity in ifc_model:
        entity_types[entity.is_a()] += 1

    total_entities = sum(entity_types.values())
    print(f"\n## Entity Statistics")
    print(f"Total Entities: {total_entities}")
    print(f"Unique Entity Types: {len(entity_types)}")

    # Key BIM entity categories
    print("\n## Key Entity Categories")

    # Spatial structure
    spatial_types = ['IfcProject', 'IfcSite', 'IfcBuilding', 'IfcBuildingStorey', 'IfcSpace']
    print("\n### Spatial Structure")
    for entity_type in spatial_types:
        count = entity_types.get(entity_type, 0)
        if count > 0:
            print(f"  {entity_type}: {count}")

    # Building elements
    element_types = [
        'IfcWall', 'IfcWallStandardCase', 'IfcSlab', 'IfcBeam', 'IfcColumn',
        'IfcDoor', 'IfcWindow', 'IfcStair', 'IfcRoof', 'IfcRailing',
        'IfcCurtainWall', 'IfcPlate', 'IfcMember', 'IfcFooting'
    ]
    print("\n### Building Elements")
    found_elements = False
    for entity_type in element_types:
        count = entity_types.get(entity_type, 0)
        if count > 0:
            print(f"  {entity_type}: {count}")
            found_elements = True
    if not found_elements:
        # Show what element types are present
        element_like = [t for t in entity_types.keys() if 'Ifc' in t and any(
            kw in t for kw in ['Wall', 'Slab', 'Beam', 'Column', 'Door', 'Window',
                               'Stair', 'Roof', 'Element', 'Member', 'Plate']
        )]
        for entity_type in sorted(element_like):
            print(f"  {entity_type}: {entity_types[entity_type]}")

    # MEP elements (if present)
    mep_types = ['IfcFlowTerminal', 'IfcFlowSegment', 'IfcFlowFitting',
                 'IfcDistributionElement', 'IfcBuildingElementProxy']
    print("\n### MEP/Other Elements")
    found_mep = False
    for entity_type in mep_types:
        count = entity_types.get(entity_type, 0)
        if count > 0:
            print(f"  {entity_type}: {count}")
            found_mep = True
    if not found_mep:
        print("  (none found)")

    # Geometry
    geometry_types = ['IfcShapeRepresentation', 'IfcExtrudedAreaSolid',
                      'IfcFacetedBrep', 'IfcPolygonalFaceSet', 'IfcTriangulatedFaceSet',
                      'IfcBooleanClippingResult', 'IfcMappedItem']
    print("\n### Geometry Representations")
    for entity_type in geometry_types:
        count = entity_types.get(entity_type, 0)
        if count > 0:
            print(f"  {entity_type}: {count}")

    # Properties
    property_types = ['IfcPropertySet', 'IfcPropertySingleValue',
                      'IfcPropertyListValue', 'IfcElementQuantity']
    print("\n### Properties & Quantities")
    for entity_type in property_types:
        count = entity_types.get(entity_type, 0)
        if count > 0:
            print(f"  {entity_type}: {count}")

    # Materials
    material_types = ['IfcMaterial', 'IfcMaterialLayer', 'IfcMaterialLayerSet',
                      'IfcMaterialLayerSetUsage', 'IfcMaterialList']
    print("\n### Materials")
    for entity_type in material_types:
        count = entity_types.get(entity_type, 0)
        if count > 0:
            print(f"  {entity_type}: {count}")

    # Classifications
    classification_types = ['IfcClassification', 'IfcClassificationReference']
    print("\n### Classifications")
    for entity_type in classification_types:
        count = entity_types.get(entity_type, 0)
        if count > 0:
            print(f"  {entity_type}: {count}")

    # Show top 20 entity types by count
    print("\n## Top 20 Entity Types by Count")
    print("-" * 40)
    for entity_type, count in entity_types.most_common(20):
        print(f"  {entity_type}: {count}")

    # Test accessing specific elements
    print("\n## Sample Element Access Test")
    print("-" * 70)

    # Get project
    projects = ifc_model.by_type('IfcProject')
    if projects:
        project = projects[0]
        print(f"\nProject: {project.Name}")
        if hasattr(project, 'Description') and project.Description:
            print(f"  Description: {project.Description}")

    # Get sites
    sites = ifc_model.by_type('IfcSite')
    if sites:
        for site in sites:
            print(f"\nSite: {site.Name}")

    # Get buildings
    buildings = ifc_model.by_type('IfcBuilding')
    if buildings:
        for building in buildings:
            print(f"\nBuilding: {building.Name}")
            if hasattr(building, 'Description') and building.Description:
                print(f"  Description: {building.Description}")

    # Get building storeys
    storeys = ifc_model.by_type('IfcBuildingStorey')
    if storeys:
        print(f"\nBuilding Storeys ({len(storeys)}):")
        for storey in storeys[:5]:  # Show first 5
            elevation = getattr(storey, 'Elevation', None)
            elev_str = f" (Elevation: {elevation})" if elevation else ""
            print(f"  - {storey.Name}{elev_str}")
        if len(storeys) > 5:
            print(f"  ... and {len(storeys) - 5} more")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"IFC File: {ifc_path.name}")
    print(f"File Size: {format_file_size(file_size)}")
    print(f"Load Time: {load_time:.2f} seconds")
    print(f"Schema: {ifc_model.schema}")
    print(f"Total Entities: {total_entities}")
    print(f"Unique Entity Types: {len(entity_types)}")

    print("\n" + "=" * 70)
    print("TEST PASSED: IFC file loaded and structure inspected successfully")
    print("=" * 70)

    return True


def main():
    """Main entry point."""
    success = test_ifc_loading()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
