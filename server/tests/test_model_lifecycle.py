"""Verify model lifecycle and extraction using real IFC fixtures."""

from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import pytest

from server.project_manager import IfcParser, ProjectManager

FIXTURE = Path(__file__).parents[2] / "test" / "fixtures" / "sample.ifc"


def test_model_load_extract_remove():
    manager = ProjectManager()
    project = manager.create_project("Review")
    assert manager.get_project(project.id) is project
    model = manager.add_model(project.id, FIXTURE.name, FIXTURE, FIXTURE.stat().st_size)
    assert project.to_dict()["models"][0]["hasSpatialTree"] is True
    tree = manager.get_spatial_tree(model.id)
    assert tree["type"] == "IfcProject"
    assert tree["children"]
    wall = model.ifc_model.by_type("IfcWall")[0]
    properties = manager.get_element_properties(model.id, wall.GlobalId)
    assert properties["modelId"] == model.id
    assert properties["globalId"] == wall.GlobalId
    assert properties["propertySets"] == []
    assert manager.get_element_properties(model.id, "0" * 22)["error"]
    assert manager.remove_model(project.id, model.id)
    assert not manager.remove_model(project.id, model.id)
    assert manager.get_spatial_tree(model.id) is None
    assert manager.get_element_properties(model.id, wall.GlobalId) is None
    assert not manager.remove_model("missing", model.id)


def test_model_limits_and_unparsed_files(tmp_path):
    manager = ProjectManager()
    with pytest.raises(ValueError, match="Project not found"):
        manager.add_model("missing", "model.ifc", FIXTURE, 0)
    project = manager.create_project("Unparsed")
    unsupported = tmp_path / "model.ifcx"
    unsupported.write_text("{}")
    model = manager.add_model(project.id, unsupported.name, unsupported, 2)
    assert model.format == "ifcx"
    assert manager.get_spatial_tree(model.id) is None
    assert manager.get_element_properties(model.id, "missing") is None
    broken = tmp_path / "broken.ifc"
    broken.write_text("invalid IFC")
    failed = manager.add_model(project.id, broken.name, broken, 11)
    assert failed.ifc_model is None
    for _ in range(8):
        manager.add_model(project.id, unsupported.name, unsupported, 2)
    with pytest.raises(ValueError, match="Maximum"):
        manager.add_model(project.id, unsupported.name, unsupported, 2)


def test_parser_extracts_type_and_material_without_internal_ids():
    model = ifcopenshell.file(schema="IFC4")
    parser = IfcParser()
    assert parser.get_spatial_tree(model).name == "(no project)"
    wall = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcWall", name="Wall"
    )
    wall_type = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcWallType", name="Type"
    )
    ifcopenshell.api.run(
        "type.assign_type", model, related_objects=[wall], relating_type=wall_type
    )
    pset = ifcopenshell.api.run(
        "pset.add_pset", model, product=wall_type, name="Pset_WallCommon"
    )
    ifcopenshell.api.run(
        "pset.edit_pset", model, pset=pset, properties={"FireRating": "60"}
    )
    material = ifcopenshell.api.run("material.add_material", model, name="Concrete")
    ifcopenshell.api.run(
        "material.assign_material",
        model,
        products=[wall],
        type="IfcMaterial",
        material=material,
    )
    result = parser.get_element_properties(model, wall.GlobalId)
    assert result["material"] == "Concrete"
    assert result["typeProperties"] == {"FireRating": "60"}
    assert all("id" not in p["properties"] for p in result["propertySets"])
