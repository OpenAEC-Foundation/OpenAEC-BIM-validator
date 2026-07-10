"""Tests for the "not checkable" honesty rule.

A specification that cannot be evaluated (e.g. its ifcVersion does not
cover the model schema) must be reported explicitly as not checkable —
never silently passed or failed.
"""

import ifcopenshell
import pytest
from ifctester.ids import Ids, Specification, Entity, Attribute

from ifc_validator.engine.validator import validate
from ifc_validator.formatters.console import format_console_to_string
from ifc_validator.formatters.html import format_html
from ifc_validator.models import SpecificationResult, ValidationResult


# -- Model-level behaviour ------------------------------------------------


def test_status_derived_from_passed_true():
    """Backward compat: status derives from passed when not given."""
    spec = SpecificationResult(
        name="s",
        passed=True,
        applicable_count=1,
        passed_count=1,
        failed_count=0,
    )
    assert spec.status == "passed"


def test_status_derived_from_passed_false():
    spec = SpecificationResult(
        name="s",
        passed=False,
        applicable_count=1,
        passed_count=0,
        failed_count=1,
    )
    assert spec.status == "failed"


def test_not_checkable_status_with_reason():
    spec = SpecificationResult(
        name="s",
        passed=False,
        status="not_checkable",
        not_checkable_reason="Specification applies to IFC4, model is IFC2X3",
        applicable_count=0,
        passed_count=0,
        failed_count=0,
    )
    assert spec.status == "not_checkable"
    assert "IFC2X3" in spec.not_checkable_reason


def test_validation_result_not_checkable_default():
    """Backward compat: existing constructors keep working."""
    result = ValidationResult(
        timestamp="2026-01-01T00:00:00",
        ifc_file="a.ifc",
        ifc_schema="IFC4",
        ifc_entity_count=1,
        ids_file="a.ids",
        validation_time_seconds=0.1,
        total_specifications=0,
        passed_specifications=0,
        failed_specifications=0,
        pass_rate_percent=0.0,
    )
    assert result.not_checkable_specifications == 0


# -- Engine-level behaviour -----------------------------------------------


@pytest.fixture
def ifc2x3_path(tmp_path):
    """Minimal valid IFC2X3 model with one wall."""
    model = ifcopenshell.file(schema="IFC2X3")
    model.create_entity(
        "IfcWall",
        GlobalId=ifcopenshell.guid.new(),
        Name="Wand-001",
    )
    path = tmp_path / "model2x3.ifc"
    model.write(str(path))
    return path


def _write_ids(tmp_path, specs):
    ids = Ids(title="Honesty test")
    for spec in specs:
        ids.specifications.append(spec)
    path = tmp_path / "rules.ids"
    ids.to_xml(str(path))
    return path


def _make_spec(name, ifc_versions):
    spec = Specification(name=name, ifcVersion=ifc_versions)
    entity = Entity()
    entity.name = "IFCWALL"
    spec.applicability.append(entity)
    attribute = Attribute()
    attribute.name = "Name"
    spec.requirements.append(attribute)
    return spec


def test_schema_mismatch_reported_not_checkable(tmp_path, ifc2x3_path):
    """An IFC4-only spec validated against IFC2X3 is not checkable."""
    ids_path = _write_ids(tmp_path, [_make_spec("ifc4-only", ["IFC4"])])

    result = validate(ifc2x3_path, ids_path)

    assert result.total_specifications == 1
    spec = result.specifications[0]
    assert spec.status == "not_checkable"
    assert spec.passed is False
    assert "IFC4" in spec.not_checkable_reason
    assert "IFC2X3" in spec.not_checkable_reason
    # Not checkable is neither passed nor failed
    assert result.passed_specifications == 0
    assert result.failed_specifications == 0
    assert result.not_checkable_specifications == 1
    # Nothing failed, so the model does not fail overall
    assert result.overall_pass is True


def test_mixed_specs_counted_separately(tmp_path, ifc2x3_path):
    """Checkable specs still validate; pass rate ignores unchecked ones."""
    ids_path = _write_ids(
        tmp_path,
        [
            _make_spec("2x3-spec", ["IFC2X3"]),
            _make_spec("ifc4-only", ["IFC4"]),
        ],
    )

    result = validate(ifc2x3_path, ids_path)

    assert result.total_specifications == 2
    by_name = {s.name: s for s in result.specifications}
    assert by_name["2x3-spec"].status == "passed"
    assert by_name["ifc4-only"].status == "not_checkable"
    assert result.passed_specifications == 1
    assert result.failed_specifications == 0
    assert result.not_checkable_specifications == 1
    # Pass rate over checkable specs only: 1/1 = 100%
    assert result.pass_rate_percent == 100.0


# -- Formatter-level behaviour --------------------------------------------


def _result_with_not_checkable():
    return ValidationResult(
        timestamp="2026-01-01T00:00:00",
        ifc_file="a.ifc",
        ifc_schema="IFC2X3",
        ifc_entity_count=1,
        ids_file="a.ids",
        validation_time_seconds=0.1,
        total_specifications=1,
        passed_specifications=0,
        failed_specifications=0,
        not_checkable_specifications=1,
        pass_rate_percent=0.0,
        overall_pass=True,
        specifications=[
            SpecificationResult(
                name="ifc4-only",
                passed=False,
                status="not_checkable",
                not_checkable_reason=(
                    "Specification applies to IFC4, but the model is IFC2X3"
                ),
                applicable_count=0,
                passed_count=0,
                failed_count=0,
            )
        ],
    )


def test_console_output_shows_not_checkable():
    output = format_console_to_string(_result_with_not_checkable())
    assert "Not checkable" in output
    assert "NOT CHECKED" in output


def test_html_output_shows_not_checkable():
    output = format_html(_result_with_not_checkable())
    assert "Not checkable" in output
    assert "NOT CHECKED" in output
