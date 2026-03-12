"""
ProjectManager — in-memory project registry with IFC model management.

Manages loaded projects and their IFC models. Provides:
- Project CRUD operations
- Model upload and lifecycle management
- Spatial tree extraction via IfcOpenShell
- Element property/pset extraction

Designed with a ModelParser abstraction for future IFCx support.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import ifcopenshell

logger = logging.getLogger(__name__)

# Maximum models per project
MAX_MODELS_PER_PROJECT = 10

# Maximum time a model stays cached (seconds)
MODEL_CACHE_TTL = 3600


class ModelParser(Protocol):
    """Abstraction for parsing model files.

    Implement this protocol to add support for new file formats (e.g., IFCx).
    """

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        ...

    def open(self, file_path: Path) -> Any:
        """Open and return a model handle."""
        ...

    def get_spatial_tree(self, model: Any) -> dict:
        """Extract the spatial hierarchy tree."""
        ...

    def get_element_properties(self, model: Any, global_id: str) -> dict:
        """Get all properties for an element by GlobalId."""
        ...


@dataclass
class SpatialNode:
    """A node in the spatial hierarchy tree."""

    global_id: str
    name: str
    type: str
    children: list["SpatialNode"] = field(default_factory=list)
    element_count: int = 0

    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        return {
            "globalId": self.global_id,
            "name": self.name,
            "type": self.type,
            "children": [c.to_dict() for c in self.children],
            "elementCount": self.element_count,
        }


@dataclass
class ModelRecord:
    """Server-side record of a loaded model."""

    id: str
    project_id: str
    file_name: str
    file_path: Path
    file_size: int
    format: str  # "ifc" or "ifcx"
    loaded_at: str
    ifc_model: ifcopenshell.file | None = None
    spatial_tree: SpatialNode | None = None


@dataclass
class ProjectRecord:
    """Server-side project record."""

    id: str
    name: str
    created_at: str
    models: list[ModelRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to serializable dict (without heavy IFC data)."""
        return {
            "id": self.id,
            "name": self.name,
            "createdAt": self.created_at,
            "models": [
                {
                    "id": m.id,
                    "fileName": m.file_name,
                    "fileSize": m.file_size,
                    "format": m.format,
                    "loadedAt": m.loaded_at,
                    "hasSpatialTree": m.spatial_tree is not None,
                }
                for m in self.models
            ],
        }


class IfcParser:
    """IFC2X3/IFC4 parser using IfcOpenShell."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a standard IFC file."""
        return file_path.suffix.lower() == ".ifc"

    def open(self, file_path: Path) -> ifcopenshell.file:
        """Open an IFC file with IfcOpenShell."""
        return ifcopenshell.open(str(file_path))

    def get_spatial_tree(self, model: ifcopenshell.file) -> SpatialNode:
        """Extract the spatial hierarchy from an IFC model.

        Traverses IfcProject -> IfcSite -> IfcBuilding -> IfcBuildingStorey.
        """
        project = model.by_type("IfcProject")
        if not project:
            return SpatialNode(
                global_id="",
                name="(no project)",
                type="IfcProject",
            )

        return self._build_spatial_node(project[0], model)

    def _build_spatial_node(
        self,
        element: ifcopenshell.entity_instance,
        model: ifcopenshell.file,
    ) -> SpatialNode:
        """Recursively build a spatial tree node."""
        name = getattr(element, "Name", None) or getattr(element, "LongName", None) or ""
        global_id = getattr(element, "GlobalId", "") or ""

        node = SpatialNode(
            global_id=global_id,
            name=str(name),
            type=element.is_a(),
        )

        # Get spatially decomposed children
        children_elements = []
        for rel in getattr(element, "IsDecomposedBy", []):
            children_elements.extend(rel.RelatedObjects)

        # Also check spatial containment (IfcRelContainedInSpatialStructure)
        contained_count = 0
        if hasattr(element, "ContainsElements"):
            for rel in element.ContainsElements:
                contained_count += len(rel.RelatedElements)

        node.element_count = contained_count

        for child in children_elements:
            child_type = child.is_a()
            # Only include spatial structure elements in the tree
            if child_type in (
                "IfcProject",
                "IfcSite",
                "IfcBuilding",
                "IfcBuildingStorey",
                "IfcSpace",
            ):
                child_node = self._build_spatial_node(child, model)
                node.children.append(child_node)

        return node

    def get_element_properties(
        self, model: ifcopenshell.file, global_id: str
    ) -> dict:
        """Get all properties for an element by GlobalId.

        Returns property sets, type properties, and material info.
        """
        try:
            element = model.by_guid(global_id)
        except RuntimeError:
            return {"error": f"Element not found: {global_id}"}

        result: dict[str, Any] = {
            "globalId": global_id,
            "entityType": element.is_a(),
            "name": getattr(element, "Name", None),
            "modelId": "",
            "propertySets": [],
            "typeProperties": {},
            "material": None,
        }

        # Extract property sets
        psets = ifcopenshell.util.element.get_psets(element)
        for pset_name, props in psets.items():
            prop_dict = {}
            for key, value in props.items():
                if key == "id":
                    continue
                prop_dict[key] = value
            result["propertySets"].append(
                {"name": pset_name, "properties": prop_dict}
            )

        # Extract type properties
        element_type = ifcopenshell.util.element.get_type(element)
        if element_type:
            type_psets = ifcopenshell.util.element.get_psets(element_type)
            for _pset_name, props in type_psets.items():
                for key, value in props.items():
                    if key == "id":
                        continue
                    result["typeProperties"][key] = value

        # Extract material
        try:
            material = ifcopenshell.util.element.get_material(element)
            if material:
                result["material"] = getattr(material, "Name", str(material))
        except (AttributeError, RuntimeError):
            pass

        return result


class ProjectManager:
    """Manages projects and their IFC models.

    Provides CRUD operations for projects and models, and delegates
    parsing to the appropriate ModelParser implementation.
    """

    def __init__(self) -> None:
        self._projects: dict[str, ProjectRecord] = {}
        self._parsers: list[IfcParser] = [IfcParser()]

    def create_project(self, name: str) -> ProjectRecord:
        """Create a new project."""
        project = ProjectRecord(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._projects[project.id] = project
        logger.info(f"Created project: {project.id} ({name})")
        return project

    def get_project(self, project_id: str) -> ProjectRecord | None:
        """Get a project by ID."""
        return self._projects.get(project_id)

    def add_model(
        self,
        project_id: str,
        file_name: str,
        file_path: Path,
        file_size: int,
    ) -> ModelRecord:
        """Add a model to a project, open it, and extract spatial tree."""
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        if len(project.models) >= MAX_MODELS_PER_PROJECT:
            raise ValueError(
                f"Maximum {MAX_MODELS_PER_PROJECT} models per project"
            )

        # Detect format
        fmt = "ifcx" if file_name.lower().endswith(".ifcx") else "ifc"

        model_record = ModelRecord(
            id=str(uuid.uuid4()),
            project_id=project_id,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            format=fmt,
            loaded_at=datetime.now(timezone.utc).isoformat(),
        )

        # Try to parse with available parsers
        for parser in self._parsers:
            if parser.can_parse(file_path):
                try:
                    ifc_model = parser.open(file_path)
                    model_record.ifc_model = ifc_model
                    model_record.spatial_tree = parser.get_spatial_tree(
                        ifc_model
                    )
                    logger.info(
                        f"Model loaded: {file_name} (project {project_id})"
                    )
                except Exception as e:
                    logger.error(f"Failed to parse {file_name}: {e}")
                break

        project.models.append(model_record)
        return model_record

    def remove_model(self, project_id: str, model_id: str) -> bool:
        """Remove a model from a project."""
        project = self._projects.get(project_id)
        if not project:
            return False

        original_count = len(project.models)
        project.models = [m for m in project.models if m.id != model_id]
        return len(project.models) < original_count

    def get_spatial_tree(
        self, model_id: str
    ) -> dict | None:
        """Get the spatial tree for a model."""
        for project in self._projects.values():
            for model in project.models:
                if model.id == model_id:
                    if model.spatial_tree:
                        return model.spatial_tree.to_dict()
                    return None
        return None

    def get_element_properties(
        self, model_id: str, global_id: str
    ) -> dict | None:
        """Get element properties by model ID and GlobalId."""
        for project in self._projects.values():
            for model in project.models:
                if model.id == model_id and model.ifc_model:
                    parser = IfcParser()
                    result = parser.get_element_properties(
                        model.ifc_model, global_id
                    )
                    result["modelId"] = model_id
                    return result
        return None
