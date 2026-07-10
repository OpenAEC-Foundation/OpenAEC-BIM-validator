"""Tests for the IFC optimizer engine (phase 1 passes).

Each pass is tested on a synthetic in-memory model with deliberately
planted defects; optimize() is tested end-to-end on the sample fixture.
"""

from pathlib import Path

import ifcopenshell
import ifcopenshell.guid
import pytest

from ifc_validator.optimizer import PASS_ORDER, list_passes, optimize
from ifc_validator.optimizer.passes import (
    compact,
    fix_duplicate_globalids,
    remove_broken_relationships,
    remove_unused_psets,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _make_model():
    """Model with planted defects: duplicate GlobalId, broken rel, orphan pset."""
    model = ifcopenshell.file(schema="IFC4")
    dup_guid = ifcopenshell.guid.new()
    wall_a = model.create_entity("IfcWall", GlobalId=dup_guid, Name="Wand-A")
    wall_b = model.create_entity("IfcWall", GlobalId=dup_guid, Name="Wand-B")
    wall_c = model.create_entity(
        "IfcWall", GlobalId=ifcopenshell.guid.new(), Name="Wand-C"
    )

    # Used pset: attached to wall_a via a valid relationship
    used_pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="Pset_Gebruikt",
        HasProperties=[],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[wall_a],
        RelatingPropertyDefinition=used_pset,
    )

    # Orphan pset: referenced by nothing
    model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="Pset_Wees",
        HasProperties=[],
    )

    # Broken relationship: empty RelatedObjects
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[],
        RelatingPropertyDefinition=used_pset,
    )

    return model, dup_guid, (wall_a, wall_b, wall_c)


def test_fix_duplicate_globalids():
    model, dup_guid, walls = _make_model()
    result = fix_duplicate_globalids(model)

    guids = [w.GlobalId for w in model.by_type("IfcWall")]
    assert len(guids) == len(set(guids)), "GlobalIds must be unique after fix"
    # First occurrence keeps the original guid
    assert walls[0].GlobalId == dup_guid
    assert walls[1].GlobalId != dup_guid
    assert result.changed == 1
    assert result.details[0]["old"] == dup_guid
    assert result.details[0]["new"] == walls[1].GlobalId


def test_fix_duplicate_globalids_noop_on_clean_model():
    model = ifcopenshell.file(schema="IFC4")
    model.create_entity(
        "IfcWall", GlobalId=ifcopenshell.guid.new(), Name="W"
    )
    result = fix_duplicate_globalids(model)
    assert result.changed == 0


def test_remove_broken_relationships():
    model, _, _ = _make_model()
    before = len(model.by_type("IfcRelDefinesByProperties"))
    result = remove_broken_relationships(model)
    after = len(model.by_type("IfcRelDefinesByProperties"))

    assert before == 2
    assert after == 1, "only the broken (empty) relationship is removed"
    assert result.changed == 1


def test_remove_unused_psets():
    model, _, _ = _make_model()
    result = remove_unused_psets(model)

    names = [p.Name for p in model.by_type("IfcPropertySet")]
    assert "Pset_Gebruikt" in names
    assert "Pset_Wees" not in names
    assert result.changed == 1


def test_compact_keeps_model_loadable(tmp_path):
    model, _, _ = _make_model()
    compacted, result = compact(model)
    out = tmp_path / "compacted.ifc"
    compacted.write(str(out))
    reloaded = ifcopenshell.open(str(out))
    assert len(reloaded.by_type("IfcWall")) == 3


def test_optimize_end_to_end(tmp_path):
    out = tmp_path / "optimized.ifc"
    report = optimize(FIXTURES / "sample.ifc", out)

    assert out.exists()
    assert report.size_before > 0
    assert report.size_after > 0
    assert report.input_file == "sample.ifc"
    assert [p.name for p in report.passes] == list(PASS_ORDER)
    reloaded = ifcopenshell.open(str(out))
    assert sum(1 for _ in reloaded) > 0


def test_optimize_subset_of_passes(tmp_path):
    out = tmp_path / "optimized.ifc"
    report = optimize(
        FIXTURES / "sample.ifc", out, passes=["fix_duplicate_globalids"]
    )
    assert [p.name for p in report.passes] == ["fix_duplicate_globalids"]
    assert out.exists()


def test_optimize_unknown_pass_raises(tmp_path):
    with pytest.raises(ValueError, match="bogus"):
        optimize(FIXTURES / "sample.ifc", tmp_path / "x.ifc", passes=["bogus"])


def test_list_passes_matches_order():
    passes = list_passes()
    assert [p["name"] for p in passes] == list(PASS_ORDER)
    for p in passes:
        assert p["title"] and p["description"]
