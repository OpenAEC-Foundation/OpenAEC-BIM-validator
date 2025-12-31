"""
IFC to Optimized Geometry Processor

This module handles server-side conversion of IFC files to browser-optimized
geometry formats (glTF or JSON mesh data) using ifcopenshell.

For the POC, we support:
1. glTF export (if ifcopenshell was compiled with glTF support)
2. JSON mesh export (triangulated geometry for Three.js)

Run as module for testing: python -m server.ifc_processor
"""

import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import ifcopenshell
import ifcopenshell.geom

# Check available serializers
GLTF_AVAILABLE = hasattr(ifcopenshell.geom.serializers, "gltf")
OBJ_AVAILABLE = hasattr(ifcopenshell.geom.serializers, "obj")


@dataclass
class ProcessingResult:
    """Container for IFC processing results."""

    success: bool
    output_format: str
    output_path: Optional[str]
    output_data: Optional[dict]
    processing_time_ms: float
    element_count: int
    vertex_count: int
    face_count: int
    error: Optional[str]
    file_size_bytes: int


@dataclass
class ElementGeometry:
    """Container for a single element's geometry data."""

    element_id: int
    element_type: str
    element_name: Optional[str]
    vertices: list[float]  # flat array: [x1,y1,z1, x2,y2,z2, ...]
    normals: list[float]  # flat array: [nx1,ny1,nz1, ...]
    indices: list[int]  # triangle indices
    material_id: Optional[str]
    color: Optional[list[float]]  # [r, g, b, a]


class IFCProcessor:
    """
    Processes IFC files to browser-optimized geometry formats.

    Supports:
    - glTF export (if available in ifcopenshell build)
    - JSON mesh export (always available)
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the IFC processor.

        Args:
            output_dir: Directory for output files. Uses temp dir if not specified.
        """
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "ifc_processed"
        self.output_dir.mkdir(exist_ok=True)

    def get_capabilities(self) -> dict:
        """Return available processing capabilities."""
        return {
            "gltf_available": GLTF_AVAILABLE,
            "obj_available": OBJ_AVAILABLE,
            "json_mesh_available": True,
            "ifcopenshell_version": ifcopenshell.version,
            "output_dir": str(self.output_dir),
        }

    def process_to_gltf(self, ifc_path: str, output_name: str) -> ProcessingResult:
        """
        Convert IFC to glTF format using ifcopenshell's built-in serializer.

        Args:
            ifc_path: Path to the IFC file
            output_name: Base name for output file (without extension)

        Returns:
            ProcessingResult with path to glTF file or error
        """
        if not GLTF_AVAILABLE:
            return ProcessingResult(
                success=False,
                output_format="gltf",
                output_path=None,
                output_data=None,
                processing_time_ms=0,
                element_count=0,
                vertex_count=0,
                face_count=0,
                error="glTF serializer not available in this ifcopenshell build",
                file_size_bytes=0,
            )

        start_time = time.time()
        output_path = self.output_dir / f"{output_name}.glb"

        try:
            # Load IFC file
            ifc_file = ifcopenshell.open(ifc_path)

            # Configure geometry settings
            geom_settings = ifcopenshell.geom.settings()
            geom_settings.set("use-world-coords", True)
            geom_settings.set("weld-vertices", True)

            # Configure serializer settings
            serializer_settings = ifcopenshell.geom.serializer_settings()

            # Create glTF serializer
            serializer = ifcopenshell.geom.serializers.gltf(
                str(output_path), geom_settings, serializer_settings
            )

            # Create iterator
            iterator = ifcopenshell.geom.iterator(
                geom_settings, ifc_file, num_threads=4
            )

            element_count = 0
            vertex_count = 0
            face_count = 0

            if iterator.initialize():
                serializer.setFile(ifc_file.wrapped_data)
                while True:
                    shape = iterator.get()
                    serializer.write(shape)
                    element_count += 1

                    # Get geometry stats
                    if hasattr(shape, "geometry"):
                        geom = shape.geometry
                        if hasattr(geom, "verts"):
                            vertex_count += len(geom.verts) // 3
                        if hasattr(geom, "faces"):
                            face_count += len(geom.faces) // 3

                    if not iterator.next():
                        break

            serializer.finalize()

            processing_time = (time.time() - start_time) * 1000
            file_size = output_path.stat().st_size if output_path.exists() else 0

            return ProcessingResult(
                success=True,
                output_format="gltf",
                output_path=str(output_path),
                output_data=None,
                processing_time_ms=round(processing_time, 2),
                element_count=element_count,
                vertex_count=vertex_count,
                face_count=face_count,
                error=None,
                file_size_bytes=file_size,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return ProcessingResult(
                success=False,
                output_format="gltf",
                output_path=None,
                output_data=None,
                processing_time_ms=round(processing_time, 2),
                element_count=0,
                vertex_count=0,
                face_count=0,
                error=str(e),
                file_size_bytes=0,
            )

    def process_to_json_mesh(self, ifc_path: str) -> ProcessingResult:
        """
        Convert IFC to JSON mesh format for Three.js consumption.

        This extracts triangulated geometry that can be directly loaded
        by Three.js BufferGeometry in the browser.

        Args:
            ifc_path: Path to the IFC file

        Returns:
            ProcessingResult with geometry data as output_data
        """
        start_time = time.time()

        try:
            # Load IFC file
            ifc_file = ifcopenshell.open(ifc_path)

            # Configure geometry settings for triangulation
            geom_settings = ifcopenshell.geom.settings()
            geom_settings.set("use-world-coords", True)
            geom_settings.set("weld-vertices", True)

            # Create iterator
            iterator = ifcopenshell.geom.iterator(
                geom_settings, ifc_file, num_threads=4
            )

            elements = []
            total_vertices = 0
            total_faces = 0

            if iterator.initialize():
                while True:
                    shape = iterator.get()

                    # Get element info
                    element = ifc_file.by_id(shape.id)
                    element_type = element.is_a() if element else "Unknown"
                    element_name = getattr(element, "Name", None) if element else None

                    # Extract geometry
                    geom = shape.geometry

                    # Get vertices (flat array)
                    vertices = list(geom.verts) if hasattr(geom, "verts") else []

                    # Get normals if available
                    normals = list(geom.normals) if hasattr(geom, "normals") else []

                    # Get face indices
                    faces = list(geom.faces) if hasattr(geom, "faces") else []

                    # Get material/color info
                    color = None
                    material_ids = []
                    if hasattr(geom, "materials") and geom.materials:
                        for mat in geom.materials:
                            if hasattr(mat, "diffuse"):
                                diffuse = mat.diffuse
                                # Handle different diffuse representations
                                try:
                                    if hasattr(diffuse, "__iter__"):
                                        color = list(diffuse)
                                    elif hasattr(diffuse, "r") and callable(diffuse.r):
                                        # r, g, b are methods on colour object
                                        color = [diffuse.r(), diffuse.g(), diffuse.b()]
                                    elif hasattr(diffuse, "r"):
                                        # r, g, b are properties
                                        color = [diffuse.r, diffuse.g, diffuse.b]
                                    else:
                                        color = [0.8, 0.8, 0.8]  # Default gray
                                except (TypeError, AttributeError):
                                    color = [0.8, 0.8, 0.8]  # Default gray

                                if color:
                                    if hasattr(mat, "transparency"):
                                        try:
                                            transp = mat.transparency
                                            if callable(transp):
                                                transp = transp()
                                            color.append(1.0 - transp)
                                        except (TypeError, AttributeError):
                                            color.append(1.0)
                                    else:
                                        color.append(1.0)
                                break

                    # Get material IDs per face if available
                    if hasattr(geom, "material_ids"):
                        material_ids = list(geom.material_ids)

                    # Skip elements with no geometry
                    if len(vertices) == 0 or len(faces) == 0:
                        if not iterator.next():
                            break
                        continue

                    # Create element geometry record
                    elem_geom = {
                        "id": shape.id,
                        "guid": shape.guid,
                        "type": element_type,
                        "name": element_name,
                        "vertices": vertices,
                        "normals": normals,
                        "indices": faces,
                        "color": color,
                    }

                    if material_ids:
                        elem_geom["materialIds"] = material_ids

                    elements.append(elem_geom)
                    total_vertices += len(vertices) // 3
                    total_faces += len(faces) // 3

                    if not iterator.next():
                        break

            processing_time = (time.time() - start_time) * 1000

            # Create output data structure
            output_data = {
                "format": "ifc-json-mesh",
                "version": "1.0",
                "source": Path(ifc_path).name,
                "schema": str(ifc_file.schema),
                "stats": {
                    "elementCount": len(elements),
                    "totalVertices": total_vertices,
                    "totalFaces": total_faces,
                    "processingTimeMs": round(processing_time, 2),
                },
                "elements": elements,
            }

            # Calculate approximate size
            data_size = len(json.dumps(output_data))

            return ProcessingResult(
                success=True,
                output_format="json-mesh",
                output_path=None,
                output_data=output_data,
                processing_time_ms=round(processing_time, 2),
                element_count=len(elements),
                vertex_count=total_vertices,
                face_count=total_faces,
                error=None,
                file_size_bytes=data_size,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return ProcessingResult(
                success=False,
                output_format="json-mesh",
                output_path=None,
                output_data=None,
                processing_time_ms=round(processing_time, 2),
                element_count=0,
                vertex_count=0,
                face_count=0,
                error=str(e),
                file_size_bytes=0,
            )

    def process(
        self, ifc_path: str, output_name: str, preferred_format: str = "auto"
    ) -> ProcessingResult:
        """
        Process IFC file to optimized geometry format.

        Args:
            ifc_path: Path to the IFC file
            output_name: Base name for output files
            preferred_format: "gltf", "json-mesh", or "auto" (tries gltf first)

        Returns:
            ProcessingResult with processing outcome
        """
        if not os.path.exists(ifc_path):
            return ProcessingResult(
                success=False,
                output_format="none",
                output_path=None,
                output_data=None,
                processing_time_ms=0,
                element_count=0,
                vertex_count=0,
                face_count=0,
                error=f"IFC file not found: {ifc_path}",
                file_size_bytes=0,
            )

        if preferred_format == "gltf":
            return self.process_to_gltf(ifc_path, output_name)
        elif preferred_format == "json-mesh":
            return self.process_to_json_mesh(ifc_path)
        else:  # auto
            # Try glTF first if available
            if GLTF_AVAILABLE:
                result = self.process_to_gltf(ifc_path, output_name)
                if result.success:
                    return result
            # Fall back to JSON mesh
            return self.process_to_json_mesh(ifc_path)


def test_processor():
    """Test the IFC processor with a sample file."""
    from pathlib import Path

    # Find test IFC file
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    test_file = project_root / "test" / "2786_CLT_model.ifc"

    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return False

    print("=" * 70)
    print("IFC Processor Test")
    print("=" * 70)

    processor = IFCProcessor()

    print("\nCapabilities:")
    caps = processor.get_capabilities()
    for key, value in caps.items():
        print(f"  {key}: {value}")

    print(f"\nProcessing: {test_file}")
    print("-" * 70)

    # Test with auto format
    result = processor.process(str(test_file), "test_output", preferred_format="auto")

    print(f"Success: {result.success}")
    print(f"Format: {result.output_format}")
    print(f"Processing time: {result.processing_time_ms:.2f} ms")
    print(f"Elements: {result.element_count}")
    print(f"Vertices: {result.vertex_count}")
    print(f"Faces: {result.face_count}")
    print(f"Output size: {result.file_size_bytes / 1024:.2f} KB")

    if result.error:
        print(f"Error: {result.error}")

    if result.output_path:
        print(f"Output file: {result.output_path}")

    if result.output_data:
        print(f"Output data elements: {len(result.output_data.get('elements', []))}")

    print("\n" + "=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)

    return result.success


if __name__ == "__main__":
    test_processor()
