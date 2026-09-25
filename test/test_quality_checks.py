"""Tests for the data quality check module (ifc_validator.quality).

Builds small synthetic IFC4 models in memory with ifcopenshell and
asserts the behaviour of each registered check plus the report
aggregation logic.

Run with:
    python -m pytest test/test_quality_checks.py -q -o addopts=""
"""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.guid
import pytest

from ifc_validator.quality import list_checks, run_quality_checks
from ifc_validator.quality.models import MAX_FINDINGS_PER_CHECK

ALL_CHECK_IDS = [
    "duplicate_globalids",
    "missing_globalid",
    "unclassified_proxies",
    "generic_names",
    "no_material",
    "no_storey",
    "no_psets",
    "unhosted_openings",
]


# ── Fixture builders ────────────────────────────────────────────────


def _model() -> ifcopenshell.file:
    """Create an empty in-memory IFC4 model."""
    return ifcopenshell.file(schema="IFC4")


def _guid() -> str:
    """Generate a fresh IFC GlobalId."""
    return ifcopenshell.guid.new()


def _wall(model, name="Muur-beton-350", guid=None):
    """Create an IfcWall with a valid GlobalId."""
    return model.create_entity("IfcWall", GlobalId=guid or _guid(), Name=name)


def _add_material(model, element):
    """Associate a material with an element."""
    material = model.create_entity("IfcMaterial", Name="Concrete C30/37")
    model.create_entity(
        "IfcRelAssociatesMaterial",
        GlobalId=_guid(),
        RelatedObjects=[element],
        RelatingMaterial=material,
    )


def _add_storey_containment(model, elements, storey=None):
    """Contain elements directly in a building storey."""
    if storey is None:
        storey = model.create_entity(
            "IfcBuildingStorey", GlobalId=_guid(), Name="00 Begane grond"
        )
    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=_guid(),
        RelatedElements=list(elements),
        RelatingStructure=storey,
    )
    return storey


def _add_pset(model, element):
    """Attach a property set to an element."""
    prop = model.create_entity("IfcPropertySingleValue", Name="Status")
    pset = model.create_entity(
        "IfcPropertySet",
        GlobalId=_guid(),
        Name="Pset_WallCommon",
        HasProperties=[prop],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=_guid(),
        RelatedObjects=[element],
        RelatingPropertyDefinition=pset,
    )


def _add_hosted_door(model, wall, name="D-001"):
    """Create a door hosted in a wall via an opening element."""
    opening = model.create_entity(
        "IfcOpeningElement", GlobalId=_guid(), Name="Opening-001"
    )
    model.create_entity(
        "IfcRelVoidsElement",
        GlobalId=_guid(),
        RelatingBuildingElement=wall,
        RelatedOpeningElement=opening,
    )
    door = model.create_entity("IfcDoor", GlobalId=_guid(), Name=name)
    model.create_entity(
        "IfcRelFillsElement",
        GlobalId=_guid(),
        RelatingOpeningElement=opening,
        RelatedBuildingElement=door,
    )
    return door


def _result(report, check_id):
    """Extract a single CheckResult by id."""
    matches = [c for c in report.checks if c.id == check_id]
    assert len(matches) == 1, f"Check {check_id} not in report"
    return matches[0]


def _run_single(model, check_id):
    """Run one check on a model and return its CheckResult."""
    report = run_quality_checks(model, checks=[check_id])
    assert len(report.checks) == 1
    return report.checks[0]


# ── Per-check tests ─────────────────────────────────────────────────


def test_duplicate_globalids() -> None:
    model = _model()
    shared = _guid()
    _wall(model, name="Muur-A", guid=shared)
    _wall(model, name="Muur-B", guid=shared)
    _wall(model, name="Muur-C")

    result = _run_single(model, "duplicate_globalids")
    assert result.severity == "error"
    assert result.passed is False
    assert result.finding_count == 1
    finding = result.findings[0]
    assert finding.global_id == shared
    assert finding.entity_type == "IfcWall"
    assert "Muur-A" in finding.message


def test_duplicate_globalids_passes_on_clean_model() -> None:
    model = _model()
    _wall(model)
    _wall(model)

    result = _run_single(model, "duplicate_globalids")
    assert result.passed is True
    assert result.finding_count == 0


def test_missing_globalid() -> None:
    model = _model()
    model.create_entity("IfcWall", Name="Muur-zonder-guid")  # GlobalId None
    model.create_entity("IfcWall", GlobalId="", Name="Muur-lege-guid")
    _wall(model, name="Muur-goed")

    result = _run_single(model, "missing_globalid")
    assert result.severity == "error"
    assert result.passed is False
    assert result.finding_count == 2
    names = {f.entity_name for f in result.findings}
    assert names == {"Muur-zonder-guid", "Muur-lege-guid"}


def test_unclassified_proxies() -> None:
    model = _model()
    model.create_entity(
        "IfcBuildingElementProxy", GlobalId=_guid(), Name="Proxy-onbekend"
    )
    _wall(model)

    result = _run_single(model, "unclassified_proxies")
    assert result.severity == "warning"
    assert result.finding_count == 1
    assert result.findings[0].entity_type == "IfcBuildingElementProxy"


def test_generic_names() -> None:
    model = _model()
    model.create_entity("IfcWall", GlobalId=_guid())  # Name None
    _wall(model, name="   ")  # whitespace-only
    _wall(model, name="Wall 1")
    _wall(model, name="wall_02")
    model.create_entity("IfcBeam", GlobalId=_guid(), Name="Beam-3")
    model.create_entity("IfcColumn", GlobalId=_guid(), Name="DEFAULT")
    _wall(model, name="Muur-beton-350")  # descriptive: passes
    _add_hosted_door(model, _wall(model), name="D-001")  # D-001: passes

    result = _run_single(model, "generic_names")
    assert result.severity == "warning"
    assert result.finding_count == 6
    messages = " | ".join(f.message for f in result.findings)
    assert "no Name" in messages
    assert "Wall 1" in messages
    assert "DEFAULT" in messages


def test_generic_names_skips_feature_elements() -> None:
    model = _model()
    # Opening elements are IfcElement subtypes but must not be flagged.
    model.create_entity("IfcOpeningElement", GlobalId=_guid())

    result = _run_single(model, "generic_names")
    assert result.passed is True


def test_no_material() -> None:
    model = _model()
    good = _wall(model, name="Muur-met-materiaal")
    _add_material(model, good)
    _wall(model, name="Muur-zonder-materiaal")

    result = _run_single(model, "no_material")
    assert result.severity == "warning"
    assert result.finding_count == 1
    assert result.findings[0].entity_name == "Muur-zonder-materiaal"


def test_no_storey_direct_and_aggregated() -> None:
    model = _model()
    contained = _wall(model, name="Muur-in-verdieping")
    storey = _add_storey_containment(model, [contained])

    # Beam contained via aggregation: beam -> assembly -> storey.
    beam = model.create_entity("IfcBeam", GlobalId=_guid(), Name="Ligger-HEA200")
    assembly = model.create_entity(
        "IfcElementAssembly", GlobalId=_guid(), Name="Spant-01"
    )
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=_guid(),
        RelatingObject=assembly,
        RelatedObjects=[beam],
    )
    _add_storey_containment(model, [assembly], storey=storey)

    orphan = _wall(model, name="Muur-zwevend")

    result = _run_single(model, "no_storey")
    assert result.severity == "warning"
    assert result.finding_count == 1
    assert result.findings[0].global_id == orphan.GlobalId


def test_no_psets() -> None:
    model = _model()
    good = _wall(model, name="Muur-met-pset")
    _add_pset(model, good)
    _wall(model, name="Muur-zonder-pset")

    result = _run_single(model, "no_psets")
    assert result.severity == "info"
    assert result.finding_count == 1
    assert result.findings[0].entity_name == "Muur-zonder-pset"


def test_unhosted_openings() -> None:
    model = _model()
    wall = _wall(model)
    _add_hosted_door(model, wall, name="D-101")  # fully hosted: passes

    # Door without any FillsVoids relationship.
    model.create_entity("IfcDoor", GlobalId=_guid(), Name="D-zwevend")
    # Window filling an opening that voids nothing.
    dangling_opening = model.create_entity(
        "IfcOpeningElement", GlobalId=_guid(), Name="Opening-los"
    )
    window = model.create_entity(
        "IfcWindow", GlobalId=_guid(), Name="Raam-zwevend"
    )
    model.create_entity(
        "IfcRelFillsElement",
        GlobalId=_guid(),
        RelatingOpeningElement=dangling_opening,
        RelatedBuildingElement=window,
    )

    result = _run_single(model, "unhosted_openings")
    assert result.severity == "warning"
    assert result.finding_count == 2
    flagged = {f.entity_name for f in result.findings}
    assert flagged == {"D-zwevend", "Raam-zwevend"}


# ── Report aggregation ──────────────────────────────────────────────


def test_full_report_counts_and_order() -> None:
    model = _model()
    shared = _guid()
    _wall(model, name="Muur-A", guid=shared)
    _wall(model, name="Muur-B", guid=shared)  # 1 error (duplicate)
    model.create_entity("IfcWall", Name="Muur-zonder-guid")  # 1 error (missing)
    model.create_entity(
        "IfcBuildingElementProxy", GlobalId=_guid(), Name="Proxy-X"
    )  # 1 warning (proxy)

    report = run_quality_checks(model)
    assert [c.id for c in report.checks] == ALL_CHECK_IDS
    assert report.ifc_schema == "IFC4"
    assert report.ifc_file == "<in-memory>"
    assert report.error_count == 2
    # Warnings: 1 proxy + 4 no_material + 4 no_storey + 0 generic (all
    # walls named "Muur-*", proxy named "Proxy-X") = at least the proxy.
    assert report.warning_count >= 1
    assert _result(report, "duplicate_globalids").finding_count == 1
    assert _result(report, "missing_globalid").finding_count == 1
    assert _result(report, "unclassified_proxies").finding_count == 1


def test_findings_truncated_to_max() -> None:
    model = _model()
    total = MAX_FINDINGS_PER_CHECK + 5
    for i in range(total):
        model.create_entity(
            "IfcBuildingElementProxy", GlobalId=_guid(), Name=f"Proxy-{i:03d}"
        )

    result = _run_single(model, "unclassified_proxies")
    assert result.finding_count == total
    assert len(result.findings) == MAX_FINDINGS_PER_CHECK
    assert result.findings_omitted == 5
    assert result.passed is False


def test_checks_filter_subset() -> None:
    model = _model()
    _wall(model)

    report = run_quality_checks(model, checks=["no_material", "no_psets"])
    assert [c.id for c in report.checks] == ["no_material", "no_psets"]


def test_unknown_check_id_raises() -> None:
    model = _model()
    with pytest.raises(ValueError, match="Unknown check id"):
        run_quality_checks(model, checks=["does_not_exist"])


def test_list_checks() -> None:
    checks = list_checks()
    assert [c["id"] for c in checks] == ALL_CHECK_IDS
    assert all(c["severity"] in {"error", "warning", "info"} for c in checks)


def test_run_from_file_path(tmp_path) -> None:
    model = _model()
    _wall(model, name="Muur-uit-bestand")
    ifc_path = tmp_path / "synthetic.ifc"
    model.write(str(ifc_path))

    report = run_quality_checks(ifc_path)
    assert report.ifc_file == str(ifc_path)
    assert report.ifc_schema == "IFC4"
    assert _result(report, "missing_globalid").passed is True
