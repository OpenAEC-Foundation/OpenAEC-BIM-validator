"""Unit tests for validation result Pydantic models.

Tests cover:
- Model instantiation for all 4 models (ValidationResult, SpecificationResult,
  RequirementResult, ElementResult)
- Enum types (SeverityLevel, ValidationStatus)
- JSON serialization (.model_dump_json())
- Field validation (required fields, types)
- Optional fields (global_id, element_name)
- Nested model hierarchy
- Round-trip serialization

Usage:
    pytest test/test_validation_models.py -v
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add server to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.models import (
    ElementResult,
    RequirementResult,
    SeverityLevel,
    SpecificationResult,
    ValidationResult,
    ValidationStatus,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_element_result():
    """Create a sample ElementResult for testing."""
    return ElementResult(
        global_id="2O2Fr$t4X7Zf8NOew3FNr2",
        element_type="IfcWall",
        element_name="Wall-001",
        status=ValidationStatus.PASS,
        messages=[],
    )


@pytest.fixture
def sample_failed_element_result():
    """Create a sample failed ElementResult for testing."""
    return ElementResult(
        global_id="3P3Gs$u5Y8Ag9OPfx4GOt3",
        element_type="IfcDoor",
        element_name="Door-001",
        status=ValidationStatus.FAIL,
        messages=["Missing required property: FireRating", "Name does not match pattern"],
    )


@pytest.fixture
def sample_requirement_result(sample_element_result, sample_failed_element_result):
    """Create a sample RequirementResult with elements."""
    return RequirementResult(
        requirement_description="All walls must have FireRating property",
        status=ValidationStatus.FAIL,
        total_elements=2,
        failed_elements=1,
        elements=[sample_element_result, sample_failed_element_result],
    )


@pytest.fixture
def sample_specification_result(sample_requirement_result):
    """Create a sample SpecificationResult with requirements."""
    return SpecificationResult(
        specification_name="Fire Safety Requirements",
        severity=SeverityLevel.ERROR,
        status=ValidationStatus.FAIL,
        total_requirements=1,
        failed_requirements=1,
        requirements=[sample_requirement_result],
    )


@pytest.fixture
def sample_validation_result(sample_specification_result):
    """Create a sample ValidationResult with full hierarchy."""
    return ValidationResult(
        success=False,
        total_specifications=1,
        failed_specifications=1,
        total_elements_validated=2,
        validation_timestamp=datetime.now().isoformat(),
        specifications=[sample_specification_result],
        ifc_file_name="test_model.ifc",
        ids_file_name="fire_safety.ids",
    )


# =============================================================================
# Enum Tests
# =============================================================================


class TestSeverityLevel:
    """Test SeverityLevel enum."""

    def test_severity_level_values(self):
        """Test that SeverityLevel has correct values."""
        assert SeverityLevel.ERROR.value == "error"
        assert SeverityLevel.WARNING.value == "warning"
        assert SeverityLevel.INFO.value == "info"

    def test_severity_level_is_string_enum(self):
        """Test that SeverityLevel inherits from str."""
        assert isinstance(SeverityLevel.ERROR, str)
        assert SeverityLevel.ERROR == "error"

    def test_severity_level_all_values(self):
        """Test that all expected severity levels exist."""
        expected_values = {"error", "warning", "info"}
        actual_values = {level.value for level in SeverityLevel}
        assert actual_values == expected_values


class TestValidationStatus:
    """Test ValidationStatus enum."""

    def test_validation_status_values(self):
        """Test that ValidationStatus has correct values."""
        assert ValidationStatus.PASS.value == "pass"
        assert ValidationStatus.FAIL.value == "fail"
        assert ValidationStatus.NOT_APPLICABLE.value == "not_applicable"

    def test_validation_status_is_string_enum(self):
        """Test that ValidationStatus inherits from str."""
        assert isinstance(ValidationStatus.PASS, str)
        assert ValidationStatus.PASS == "pass"

    def test_validation_status_all_values(self):
        """Test that all expected validation statuses exist."""
        expected_values = {"pass", "fail", "not_applicable"}
        actual_values = {status.value for status in ValidationStatus}
        assert actual_values == expected_values


# =============================================================================
# ElementResult Model Tests
# =============================================================================


class TestElementResult:
    """Test ElementResult Pydantic model."""

    def test_element_result_creation_minimal(self):
        """Test ElementResult with required fields only."""
        elem = ElementResult(
            element_type="IfcWall",
            status=ValidationStatus.PASS,
        )

        assert elem.element_type == "IfcWall"
        assert elem.status == ValidationStatus.PASS
        assert elem.global_id is None
        assert elem.element_name is None
        assert elem.messages == []

    def test_element_result_creation_full(self, sample_element_result):
        """Test ElementResult with all fields."""
        assert sample_element_result.global_id == "2O2Fr$t4X7Zf8NOew3FNr2"
        assert sample_element_result.element_type == "IfcWall"
        assert sample_element_result.element_name == "Wall-001"
        assert sample_element_result.status == ValidationStatus.PASS
        assert sample_element_result.messages == []

    def test_element_result_with_messages(self, sample_failed_element_result):
        """Test ElementResult with failure messages."""
        assert len(sample_failed_element_result.messages) == 2
        assert "FireRating" in sample_failed_element_result.messages[0]

    def test_element_result_optional_global_id(self):
        """Test ElementResult accepts None for global_id."""
        elem = ElementResult(
            global_id=None,
            element_type="IfcSpace",
            status=ValidationStatus.NOT_APPLICABLE,
        )
        assert elem.global_id is None

    def test_element_result_optional_element_name(self):
        """Test ElementResult accepts None for element_name."""
        elem = ElementResult(
            element_type="IfcColumn",
            element_name=None,
            status=ValidationStatus.PASS,
        )
        assert elem.element_name is None

    def test_element_result_json_serialization(self, sample_element_result):
        """Test ElementResult serializes to valid JSON."""
        json_str = sample_element_result.model_dump_json()
        data = json.loads(json_str)

        assert data["element_type"] == "IfcWall"
        assert data["status"] == "pass"
        assert data["global_id"] == "2O2Fr$t4X7Zf8NOew3FNr2"

    def test_element_result_status_with_string(self):
        """Test ElementResult accepts string for status field."""
        elem = ElementResult(
            element_type="IfcBeam",
            status="fail",
        )
        assert elem.status == ValidationStatus.FAIL

    def test_element_result_required_fields_validation(self):
        """Test ElementResult raises error when required fields missing."""
        with pytest.raises(Exception):
            ElementResult(status=ValidationStatus.PASS)

        with pytest.raises(Exception):
            ElementResult(element_type="IfcWall")


# =============================================================================
# RequirementResult Model Tests
# =============================================================================


class TestRequirementResult:
    """Test RequirementResult Pydantic model."""

    def test_requirement_result_creation_minimal(self):
        """Test RequirementResult with required fields only."""
        req = RequirementResult(
            requirement_description="Test requirement",
            status=ValidationStatus.PASS,
            total_elements=0,
            failed_elements=0,
        )

        assert req.requirement_description == "Test requirement"
        assert req.status == ValidationStatus.PASS
        assert req.total_elements == 0
        assert req.failed_elements == 0
        assert req.elements == []

    def test_requirement_result_with_elements(self, sample_requirement_result):
        """Test RequirementResult with element results."""
        assert len(sample_requirement_result.elements) == 2
        assert sample_requirement_result.total_elements == 2
        assert sample_requirement_result.failed_elements == 1

    def test_requirement_result_empty_elements(self):
        """Test RequirementResult with empty elements list."""
        req = RequirementResult(
            requirement_description="No applicable elements",
            status=ValidationStatus.NOT_APPLICABLE,
            total_elements=0,
            failed_elements=0,
            elements=[],
        )
        assert req.elements == []

    def test_requirement_result_json_serialization(self, sample_requirement_result):
        """Test RequirementResult serializes to valid JSON."""
        json_str = sample_requirement_result.model_dump_json()
        data = json.loads(json_str)

        assert data["requirement_description"] == "All walls must have FireRating property"
        assert data["status"] == "fail"
        assert data["total_elements"] == 2
        assert len(data["elements"]) == 2

    def test_requirement_result_nested_element_serialization(self, sample_requirement_result):
        """Test RequirementResult nested ElementResults serialize correctly."""
        json_str = sample_requirement_result.model_dump_json()
        data = json.loads(json_str)

        # Verify nested elements
        assert data["elements"][0]["element_type"] == "IfcWall"
        assert data["elements"][1]["element_type"] == "IfcDoor"
        assert data["elements"][1]["status"] == "fail"


# =============================================================================
# SpecificationResult Model Tests
# =============================================================================


class TestSpecificationResult:
    """Test SpecificationResult Pydantic model."""

    def test_specification_result_creation_minimal(self):
        """Test SpecificationResult with required fields only."""
        spec = SpecificationResult(
            specification_name="Test Spec",
            severity=SeverityLevel.WARNING,
            status=ValidationStatus.PASS,
            total_requirements=0,
            failed_requirements=0,
        )

        assert spec.specification_name == "Test Spec"
        assert spec.severity == SeverityLevel.WARNING
        assert spec.status == ValidationStatus.PASS
        assert spec.requirements == []

    def test_specification_result_with_requirements(self, sample_specification_result):
        """Test SpecificationResult with requirement results."""
        assert len(sample_specification_result.requirements) == 1
        assert sample_specification_result.severity == SeverityLevel.ERROR

    def test_specification_result_severity_levels(self):
        """Test SpecificationResult accepts all severity levels."""
        for severity in [SeverityLevel.ERROR, SeverityLevel.WARNING, SeverityLevel.INFO]:
            spec = SpecificationResult(
                specification_name="Test",
                severity=severity,
                status=ValidationStatus.PASS,
                total_requirements=0,
                failed_requirements=0,
            )
            assert spec.severity == severity

    def test_specification_result_severity_with_string(self):
        """Test SpecificationResult accepts string for severity field."""
        spec = SpecificationResult(
            specification_name="Test",
            severity="warning",
            status=ValidationStatus.PASS,
            total_requirements=0,
            failed_requirements=0,
        )
        assert spec.severity == SeverityLevel.WARNING

    def test_specification_result_json_serialization(self, sample_specification_result):
        """Test SpecificationResult serializes to valid JSON."""
        json_str = sample_specification_result.model_dump_json()
        data = json.loads(json_str)

        assert data["specification_name"] == "Fire Safety Requirements"
        assert data["severity"] == "error"
        assert data["status"] == "fail"
        assert len(data["requirements"]) == 1


# =============================================================================
# ValidationResult Model Tests
# =============================================================================


class TestValidationResult:
    """Test ValidationResult Pydantic model."""

    def test_validation_result_creation_minimal(self):
        """Test ValidationResult with required fields only."""
        result = ValidationResult(
            success=True,
            total_specifications=0,
            failed_specifications=0,
            total_elements_validated=0,
            validation_timestamp=datetime.now().isoformat(),
        )

        assert result.success is True
        assert result.specifications == []
        assert result.ifc_file_name is None
        assert result.ids_file_name is None

    def test_validation_result_full_hierarchy(self, sample_validation_result):
        """Test ValidationResult with complete nested hierarchy."""
        assert sample_validation_result.success is False
        assert len(sample_validation_result.specifications) == 1
        assert sample_validation_result.ifc_file_name == "test_model.ifc"
        assert sample_validation_result.ids_file_name == "fire_safety.ids"

    def test_validation_result_optional_file_names(self):
        """Test ValidationResult accepts None for file names."""
        result = ValidationResult(
            success=True,
            total_specifications=0,
            failed_specifications=0,
            total_elements_validated=0,
            validation_timestamp="2025-01-01T00:00:00",
            ifc_file_name=None,
            ids_file_name=None,
        )
        assert result.ifc_file_name is None
        assert result.ids_file_name is None

    def test_validation_result_json_serialization(self, sample_validation_result):
        """Test ValidationResult serializes to valid JSON."""
        json_str = sample_validation_result.model_dump_json()
        data = json.loads(json_str)

        assert data["success"] is False
        assert data["total_specifications"] == 1
        assert data["ifc_file_name"] == "test_model.ifc"

    def test_validation_result_timestamp_format(self):
        """Test ValidationResult accepts ISO 8601 timestamp."""
        timestamp = datetime.now().isoformat()
        result = ValidationResult(
            success=True,
            total_specifications=0,
            failed_specifications=0,
            total_elements_validated=0,
            validation_timestamp=timestamp,
        )
        assert result.validation_timestamp == timestamp


# =============================================================================
# Round-Trip Serialization Tests
# =============================================================================


class TestRoundTripSerialization:
    """Test round-trip JSON serialization and deserialization."""

    def test_element_result_round_trip(self, sample_element_result):
        """Test ElementResult survives round-trip serialization."""
        json_str = sample_element_result.model_dump_json()
        restored = ElementResult.model_validate_json(json_str)

        assert restored.global_id == sample_element_result.global_id
        assert restored.element_type == sample_element_result.element_type
        assert restored.element_name == sample_element_result.element_name
        assert restored.status == sample_element_result.status
        assert restored.messages == sample_element_result.messages

    def test_requirement_result_round_trip(self, sample_requirement_result):
        """Test RequirementResult survives round-trip serialization."""
        json_str = sample_requirement_result.model_dump_json()
        restored = RequirementResult.model_validate_json(json_str)

        assert restored.requirement_description == sample_requirement_result.requirement_description
        assert restored.total_elements == sample_requirement_result.total_elements
        assert len(restored.elements) == len(sample_requirement_result.elements)

    def test_specification_result_round_trip(self, sample_specification_result):
        """Test SpecificationResult survives round-trip serialization."""
        json_str = sample_specification_result.model_dump_json()
        restored = SpecificationResult.model_validate_json(json_str)

        assert restored.specification_name == sample_specification_result.specification_name
        assert restored.severity == sample_specification_result.severity
        assert len(restored.requirements) == len(sample_specification_result.requirements)

    def test_validation_result_round_trip(self, sample_validation_result):
        """Test ValidationResult survives round-trip serialization."""
        json_str = sample_validation_result.model_dump_json()
        restored = ValidationResult.model_validate_json(json_str)

        assert restored.success == sample_validation_result.success
        assert restored.total_specifications == sample_validation_result.total_specifications
        assert restored.ifc_file_name == sample_validation_result.ifc_file_name
        assert len(restored.specifications) == len(sample_validation_result.specifications)

    def test_full_hierarchy_round_trip(self, sample_validation_result):
        """Test full nested hierarchy survives round-trip serialization."""
        json_str = sample_validation_result.model_dump_json()
        restored = ValidationResult.model_validate_json(json_str)

        # Verify full nested hierarchy
        spec = restored.specifications[0]
        assert spec.specification_name == "Fire Safety Requirements"

        req = spec.requirements[0]
        assert req.requirement_description == "All walls must have FireRating property"

        elem = req.elements[0]
        assert elem.element_type == "IfcWall"


# =============================================================================
# JSON Schema Tests
# =============================================================================


class TestJsonSchema:
    """Test JSON schema generation for API documentation."""

    def test_element_result_schema(self):
        """Test ElementResult generates valid JSON schema."""
        schema = ElementResult.model_json_schema()
        assert "properties" in schema
        assert "element_type" in schema["properties"]
        assert "status" in schema["properties"]

    def test_validation_result_schema(self):
        """Test ValidationResult generates valid JSON schema."""
        schema = ValidationResult.model_json_schema()
        assert "properties" in schema
        assert "success" in schema["properties"]
        assert "specifications" in schema["properties"]

    def test_schema_includes_descriptions(self):
        """Test that schema includes field descriptions."""
        schema = ElementResult.model_json_schema()
        assert "description" in schema["properties"]["global_id"]
        assert "3D viewer" in schema["properties"]["global_id"]["description"]


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_validation_result(self):
        """Test ValidationResult with no specifications."""
        result = ValidationResult(
            success=True,
            total_specifications=0,
            failed_specifications=0,
            total_elements_validated=0,
            validation_timestamp="2025-01-01T00:00:00",
            specifications=[],
        )
        assert len(result.specifications) == 0
        assert result.success is True

    def test_large_messages_list(self):
        """Test ElementResult with many failure messages."""
        messages = [f"Error {i}: Validation failed" for i in range(100)]
        elem = ElementResult(
            element_type="IfcWall",
            status=ValidationStatus.FAIL,
            messages=messages,
        )
        assert len(elem.messages) == 100

    def test_special_characters_in_strings(self):
        """Test models handle special characters in strings."""
        elem = ElementResult(
            global_id="2O2Fr$t4X7Zf8NOew3FNr2",
            element_type="IfcWall",
            element_name='Wall with "quotes" and <brackets>',
            status=ValidationStatus.PASS,
        )

        json_str = elem.model_dump_json()
        restored = ElementResult.model_validate_json(json_str)
        assert restored.element_name == 'Wall with "quotes" and <brackets>'

    def test_unicode_in_names(self):
        """Test models handle Unicode characters."""
        elem = ElementResult(
            element_type="IfcWall",
            element_name="Muur-001 \u00e9\u00e8\u00ea",
            status=ValidationStatus.PASS,
        )

        json_str = elem.model_dump_json()
        restored = ElementResult.model_validate_json(json_str)
        assert "\u00e9" in restored.element_name

    def test_deeply_nested_hierarchy(self):
        """Test deeply nested validation result."""
        elements = [
            ElementResult(
                element_type=f"IfcWall",
                element_name=f"Wall-{i:03d}",
                status=ValidationStatus.FAIL if i % 2 == 0 else ValidationStatus.PASS,
            )
            for i in range(10)
        ]

        requirements = [
            RequirementResult(
                requirement_description=f"Requirement {i}",
                status=ValidationStatus.FAIL,
                total_elements=10,
                failed_elements=5,
                elements=elements,
            )
            for i in range(5)
        ]

        specifications = [
            SpecificationResult(
                specification_name=f"Spec {i}",
                severity=SeverityLevel.WARNING,
                status=ValidationStatus.FAIL,
                total_requirements=5,
                failed_requirements=5,
                requirements=requirements,
            )
            for i in range(3)
        ]

        result = ValidationResult(
            success=False,
            total_specifications=3,
            failed_specifications=3,
            total_elements_validated=150,
            validation_timestamp=datetime.now().isoformat(),
            specifications=specifications,
        )

        # Should serialize without error
        json_str = result.model_dump_json()
        data = json.loads(json_str)

        assert len(data["specifications"]) == 3
        assert len(data["specifications"][0]["requirements"]) == 5
        assert len(data["specifications"][0]["requirements"][0]["elements"]) == 10


# =============================================================================
# Integration Tests
# =============================================================================


class TestModelIntegration:
    """Test model integration and imports."""

    def test_all_models_importable(self):
        """Test all models can be imported from server.models."""
        from server.models import (
            ElementResult,
            RequirementResult,
            SeverityLevel,
            SpecificationResult,
            ValidationResult,
            ValidationStatus,
        )

        assert ElementResult is not None
        assert RequirementResult is not None
        assert SpecificationResult is not None
        assert ValidationResult is not None
        assert SeverityLevel is not None
        assert ValidationStatus is not None

    def test_model_inheritance(self):
        """Test models inherit from Pydantic BaseModel."""
        from pydantic import BaseModel

        assert issubclass(ElementResult, BaseModel)
        assert issubclass(RequirementResult, BaseModel)
        assert issubclass(SpecificationResult, BaseModel)
        assert issubclass(ValidationResult, BaseModel)

    def test_enum_types(self):
        """Test enums are proper Python Enum types."""
        from enum import Enum

        assert issubclass(SeverityLevel, Enum)
        assert issubclass(ValidationStatus, Enum)
        assert issubclass(SeverityLevel, str)
        assert issubclass(ValidationStatus, str)
