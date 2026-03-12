"""Unit tests for the ifc_validator.validator module.

Tests cover:
- Memory check function (check_memory_available, get_memory_info)
- File validation functions (validate_file_exists, validate_ifc_extension, validate_ids_extension)
- IFC-IDS validation workflow (validate, load_ifc_model, load_ids_specification)
- Result dataclasses (EntityFailure, SpecificationResult, ValidationResult)
- CRITICAL: Verify code uses spec.failed_entities NOT spec.failed_elements

Usage:
    pytest test/test_validator.py -v
    pytest test/test_validator.py --cov=src --cov-report=term-missing
"""

import os
import sys
import tempfile


from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ifc_validator.validator import (
    IFC_MEMORY_EXPANSION_FACTOR,
    VALID_IDS_EXTENSIONS,
    VALID_IFC_EXTENSIONS,
    EntityFailure,
    SpecificationResult,
    ValidationResult,
    _extract_entity_failure,
    check_memory_available,
    get_memory_info,
    load_ifc_model,
    load_ids_specification,
    validate,
    validate_file_exists,
    validate_ids_extension,
    validate_ids_file,
    validate_ifc_extension,
    validate_ifc_file,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_ifc_path():
    """Path to sample IFC file that passes validation."""
    return Path(__file__).parent / "fixtures" / "sample.ifc"


@pytest.fixture
def sample_fail_ifc_path():
    """Path to sample IFC file that fails validation."""
    return Path(__file__).parent / "fixtures" / "sample-fail.ifc"


@pytest.fixture
def sample_ids_path():
    """Path to sample IDS file."""
    return Path(__file__).parent / "fixtures" / "sample.ids"


@pytest.fixture
def temp_ifc_file():
    """Create a temporary file with .ifc extension."""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        f.write(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;")
        temp_path = f.name
    yield Path(temp_path)
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_ids_file():
    """Create a temporary file with .ids extension."""
    with tempfile.NamedTemporaryFile(suffix=".ids", delete=False) as f:
        f.write(b"<ids></ids>")
        temp_path = f.name
    yield Path(temp_path)
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_invalid_extension_file():
    """Create a temporary file with invalid extension."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Not an IFC file")
        temp_path = f.name
    yield Path(temp_path)
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# =============================================================================
# Constants Tests
# =============================================================================


class TestValidatorConstants:
    """Test validator module constants."""

    def test_valid_ifc_extensions(self):
        """Test that valid IFC extensions are defined correctly."""
        assert VALID_IFC_EXTENSIONS == {".ifc", ".ifcxml", ".ifczip"}

    def test_valid_ids_extensions(self):
        """Test that valid IDS extensions are defined correctly."""
        assert VALID_IDS_EXTENSIONS == {".ids"}

    def test_memory_expansion_factor(self):
        """Test that memory expansion factor is 10x as per spec."""
        assert IFC_MEMORY_EXPANSION_FACTOR == 10


# =============================================================================
# Memory Check Function Tests
# =============================================================================


class TestMemoryCheck:
    """Test memory check function."""

    def test_check_memory_available_returns_bool(self, sample_ifc_path):
        """Test that check_memory_available returns boolean."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = check_memory_available(sample_ifc_path)
        assert isinstance(result, bool)

    def test_check_memory_available_for_small_file(self, sample_ifc_path):
        """Test that small files pass memory check."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        # Small test files should pass memory check
        result = check_memory_available(sample_ifc_path)
        assert result is True

    def test_check_memory_available_nonexistent_file(self):
        """Test that nonexistent file returns False."""
        result = check_memory_available("/nonexistent/path/file.ifc")
        assert result is False

    def test_check_memory_available_uses_10x_factor(self, temp_ifc_file):
        """Test that memory check correctly uses 10x expansion factor."""
        file_size = temp_ifc_file.stat().st_size

        with patch("psutil.virtual_memory") as mock_memory:
            # Mock memory just below required threshold
            mock_memory.return_value = MagicMock(
                available=file_size * IFC_MEMORY_EXPANSION_FACTOR - 1
            )
            result = check_memory_available(temp_ifc_file)
            assert result is False

            # Mock memory just above required threshold
            mock_memory.return_value = MagicMock(
                available=file_size * IFC_MEMORY_EXPANSION_FACTOR + 1
            )
            result = check_memory_available(temp_ifc_file)
            assert result is True

    def test_get_memory_info_returns_dict(self, sample_ifc_path):
        """Test that get_memory_info returns dictionary with expected keys."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = get_memory_info(sample_ifc_path)

        assert isinstance(result, dict)
        assert "file_size" in result
        assert "available_memory" in result
        assert "required_memory" in result
        assert "is_sufficient" in result

    def test_get_memory_info_calculates_required_memory(self, sample_ifc_path):
        """Test that get_memory_info calculates required_memory as 10x file_size."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = get_memory_info(sample_ifc_path)

        expected_required = result["file_size"] * IFC_MEMORY_EXPANSION_FACTOR
        assert result["required_memory"] == expected_required

    def test_get_memory_info_nonexistent_file(self):
        """Test get_memory_info with nonexistent file."""
        result = get_memory_info("/nonexistent/path/file.ifc")

        assert result["file_size"] == 0
        assert result["required_memory"] == 0
        assert result["is_sufficient"] is False
        assert "error" in result

    def test_get_memory_info_includes_mb_values(self, sample_ifc_path):
        """Test that get_memory_info includes MB-formatted values."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = get_memory_info(sample_ifc_path)

        assert "file_size_mb" in result
        assert "available_memory_mb" in result
        assert "required_memory_mb" in result


# =============================================================================
# File Validation Tests
# =============================================================================


class TestFileValidation:
    """Test file validation functions."""

    def test_validate_file_exists_success(self, sample_ifc_path):
        """Test validate_file_exists with existing file."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = validate_file_exists(sample_ifc_path, "IFC")
        assert result == sample_ifc_path

    def test_validate_file_exists_nonexistent(self):
        """Test validate_file_exists raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_file_exists("/nonexistent/path/file.ifc", "IFC")

        assert "IFC" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_validate_file_exists_directory(self):
        """Test validate_file_exists raises error for directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError) as exc_info:
                validate_file_exists(tmpdir, "Test")

            assert "not a file" in str(exc_info.value)

    def test_validate_ifc_extension_valid(self):
        """Test validate_ifc_extension accepts valid extensions."""
        for ext in [".ifc", ".ifcxml", ".ifczip"]:
            path = Path(f"/some/path/model{ext}")
            result = validate_ifc_extension(path)
            assert result.suffix.lower() == ext

    def test_validate_ifc_extension_case_insensitive(self):
        """Test validate_ifc_extension is case insensitive."""
        for ext in [".IFC", ".IFCXML", ".IFCZIP", ".Ifc"]:
            path = Path(f"/some/path/model{ext}")
            result = validate_ifc_extension(path)
            assert result is not None

    def test_validate_ifc_extension_invalid(self):
        """Test validate_ifc_extension rejects invalid extensions."""
        with pytest.raises(ValueError) as exc_info:
            validate_ifc_extension(Path("/some/path/model.txt"))

        assert "extension" in str(exc_info.value).lower()
        assert ".txt" in str(exc_info.value)

    def test_validate_ids_extension_valid(self):
        """Test validate_ids_extension accepts .ids extension."""
        path = Path("/some/path/rules.ids")
        result = validate_ids_extension(path)
        assert result.suffix.lower() == ".ids"

    def test_validate_ids_extension_case_insensitive(self):
        """Test validate_ids_extension is case insensitive."""
        for ext in [".IDS", ".Ids", ".iDS"]:
            path = Path(f"/some/path/rules{ext}")
            result = validate_ids_extension(path)
            assert result is not None

    def test_validate_ids_extension_invalid(self):
        """Test validate_ids_extension rejects non-.ids extensions."""
        with pytest.raises(ValueError) as exc_info:
            validate_ids_extension(Path("/some/path/rules.xml"))

        assert "extension" in str(exc_info.value).lower()
        assert ".xml" in str(exc_info.value)


# =============================================================================
# Combined Validation Tests
# =============================================================================


class TestCombinedValidation:
    """Test combined validation functions."""

    def test_validate_ifc_file_success(self, sample_ifc_path):
        """Test validate_ifc_file with valid file."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = validate_ifc_file(sample_ifc_path)
        assert result == sample_ifc_path

    def test_validate_ifc_file_not_found(self):
        """Test validate_ifc_file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            validate_ifc_file("/nonexistent/model.ifc")

    def test_validate_ifc_file_invalid_extension(self, temp_invalid_extension_file):
        """Test validate_ifc_file raises ValueError for invalid extension."""
        with pytest.raises(ValueError):
            validate_ifc_file(temp_invalid_extension_file)

    def test_validate_ifc_file_memory_error(self, sample_ifc_path):
        """Test validate_ifc_file raises MemoryError when insufficient memory."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        with patch("ifc_validator.engine.file_utils.check_memory_available", return_value=False):
            with patch("ifc_validator.engine.file_utils.get_memory_info", return_value={
                "file_size_mb": 100,
                "required_memory_mb": 1000,
                "available_memory_mb": 500,
            }):
                with pytest.raises(MemoryError) as exc_info:
                    validate_ifc_file(sample_ifc_path)

                assert "memory" in str(exc_info.value).lower()

    def test_validate_ids_file_success(self, sample_ids_path):
        """Test validate_ids_file with valid file."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate_ids_file(sample_ids_path)
        assert result == sample_ids_path

    def test_validate_ids_file_not_found(self):
        """Test validate_ids_file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            validate_ids_file("/nonexistent/rules.ids")

    def test_validate_ids_file_invalid_extension(self, temp_invalid_extension_file):
        """Test validate_ids_file raises ValueError for invalid extension."""
        with pytest.raises(ValueError):
            validate_ids_file(temp_invalid_extension_file)


# =============================================================================
# Result Dataclasses Tests
# =============================================================================


class TestResultDataclasses:
    """Test validation result dataclasses."""

    def test_entity_failure_creation(self):
        """Test EntityFailure dataclass creation."""
        failure = EntityFailure(
            entity_id=123,
            entity_type="IfcWall",
            entity_name="W-001",
            global_id="0a1b2c3d",
        )

        assert failure.entity_id == 123
        assert failure.entity_type == "IfcWall"
        assert failure.entity_name == "W-001"
        assert failure.global_id == "0a1b2c3d"

    def test_entity_failure_optional_fields(self):
        """Test EntityFailure with None optional fields."""
        failure = EntityFailure(
            entity_id=123,
            entity_type="IfcWall",
            entity_name=None,
            global_id=None,
        )

        assert failure.entity_name is None
        assert failure.global_id is None

    def test_specification_result_creation(self):
        """Test SpecificationResult dataclass creation."""
        spec_result = SpecificationResult(
            name="Test Specification",
            description="A test specification",
            passed=True,
            applicable_count=10,
            passed_count=10,
            failed_count=0,
            failures=[],
        )

        assert spec_result.name == "Test Specification"
        assert spec_result.description == "A test specification"
        assert spec_result.passed is True
        assert spec_result.applicable_count == 10
        assert spec_result.passed_count == 10
        assert spec_result.failed_count == 0
        assert spec_result.failures == []

    def test_specification_result_with_failures(self):
        """Test SpecificationResult with failure details."""
        failure = EntityFailure(
            entity_id=123,
            entity_type="IfcWall",
            entity_name="Bad Wall",
            global_id="abc123",
        )
        spec_result = SpecificationResult(
            name="Naming Convention",
            description=None,
            passed=False,
            applicable_count=5,
            passed_count=4,
            failed_count=1,
            failures=[failure],
        )

        assert spec_result.passed is False
        assert len(spec_result.failures) == 1
        assert spec_result.failures[0].entity_name == "Bad Wall"

    def test_specification_result_default_failures(self):
        """Test SpecificationResult default failures list."""
        spec_result = SpecificationResult(
            name="Test",
            description=None,
            passed=True,
            applicable_count=0,
            passed_count=0,
            failed_count=0,
        )

        assert spec_result.failures == []

    def test_validation_result_creation(self):
        """Test ValidationResult dataclass creation."""
        result = ValidationResult(
            timestamp="2025-01-01T12:00:00",
            ifc_file="model.ifc",
            ifc_schema="IFC4",
            ifc_entity_count=100,
            ids_file="rules.ids",
            ids_title="Test Rules",
            validation_time_seconds=1.5,
            total_specifications=3,
            passed_specifications=3,
            failed_specifications=0,
            pass_rate_percent=100.0,
            specifications=[],
            overall_pass=True,
        )

        assert result.ifc_file == "model.ifc"
        assert result.ifc_schema == "IFC4"
        assert result.overall_pass is True
        assert result.pass_rate_percent == 100.0

    def test_validation_result_default_values(self):
        """Test ValidationResult with default values."""
        result = ValidationResult(
            timestamp="2025-01-01T12:00:00",
            ifc_file="model.ifc",
            ifc_schema="IFC4",
            ifc_entity_count=100,
            ids_file="rules.ids",
            ids_title=None,
            validation_time_seconds=1.0,
            total_specifications=0,
            passed_specifications=0,
            failed_specifications=0,
            pass_rate_percent=0.0,
        )

        assert result.specifications == []
        assert result.overall_pass is True

    def test_validation_result_json_serializable(self):
        """Test ValidationResult can be serialized to dict for JSON."""
        failure = EntityFailure(
            entity_id=123,
            entity_type="IfcWall",
            entity_name="Bad Wall",
            global_id="abc123",
        )
        spec = SpecificationResult(
            name="Test",
            description="Test spec",
            passed=False,
            applicable_count=1,
            passed_count=0,
            failed_count=1,
            failures=[failure],
        )
        result = ValidationResult(
            timestamp="2025-01-01T12:00:00",
            ifc_file="model.ifc",
            ifc_schema="IFC4",
            ifc_entity_count=100,
            ids_file="rules.ids",
            ids_title="Test",
            validation_time_seconds=1.0,
            total_specifications=1,
            passed_specifications=0,
            failed_specifications=1,
            pass_rate_percent=0.0,
            specifications=[spec],
            overall_pass=False,
        )

        # Convert to dict for JSON serialization
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["overall_pass"] is False
        assert len(data["specifications"]) == 1
        assert len(data["specifications"][0]["failures"]) == 1


# =============================================================================
# Validation Workflow Tests
# =============================================================================


class TestValidationWorkflow:
    """Test IFC-IDS validation workflow."""

    def test_load_ifc_model_success(self, sample_ifc_path):
        """Test loading IFC model successfully."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        model = load_ifc_model(sample_ifc_path)
        assert model is not None

    def test_load_ifc_model_invalid_file(self, temp_invalid_extension_file):
        """Test load_ifc_model raises RuntimeError for invalid file."""
        # Rename to .ifc to bypass extension check
        with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
            f.write(b"Invalid IFC content")
            temp_path = f.name

        try:
            with pytest.raises(RuntimeError) as exc_info:
                load_ifc_model(temp_path)

            assert "parse" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_ids_specification_success(self, sample_ids_path):
        """Test loading IDS specification successfully."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        ids_spec = load_ids_specification(sample_ids_path)
        assert ids_spec is not None

    def test_load_ids_specification_invalid_file(self):
        """Test load_ids_specification raises RuntimeError for invalid file."""
        with tempfile.NamedTemporaryFile(suffix=".ids", delete=False) as f:
            f.write(b"Invalid IDS content")
            temp_path = f.name

        try:
            with pytest.raises(RuntimeError) as exc_info:
                load_ids_specification(temp_path)

            assert "parse" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_validate_returns_validation_result(self, sample_ifc_path, sample_ids_path):
        """Test validate function returns ValidationResult."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        assert isinstance(result, ValidationResult)
        assert result.ifc_file == sample_ifc_path.name
        assert result.ids_file == sample_ids_path.name

    def test_validate_passing_model(self, sample_ifc_path, sample_ids_path):
        """Test validation with a passing model returns overall_pass=True."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        # sample.ifc has wall with 'W-001' which should pass
        assert result.overall_pass is True
        assert result.failed_specifications == 0

    def test_validate_failing_model(self, sample_fail_ifc_path, sample_ids_path):
        """Test validation with a failing model returns overall_pass=False."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_fail_ifc_path, sample_ids_path)

        # sample-fail.ifc has wall with 'Bad Wall Name' which should fail
        assert result.overall_pass is False
        assert result.failed_specifications > 0

    def test_validate_includes_timing(self, sample_ifc_path, sample_ids_path):
        """Test validation result includes timing information."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        assert result.validation_time_seconds >= 0
        assert isinstance(result.validation_time_seconds, float)

    def test_validate_includes_timestamp(self, sample_ifc_path, sample_ids_path):
        """Test validation result includes ISO timestamp."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        # Should be parseable as ISO datetime
        datetime.fromisoformat(result.timestamp)

    def test_validate_includes_ifc_schema(self, sample_ifc_path, sample_ids_path):
        """Test validation result includes IFC schema version."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        assert result.ifc_schema is not None
        assert "IFC" in result.ifc_schema.upper()

    def test_validate_includes_specifications(self, sample_ifc_path, sample_ids_path):
        """Test validation result includes specification results."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        assert result.total_specifications > 0
        assert len(result.specifications) == result.total_specifications
        assert all(isinstance(s, SpecificationResult) for s in result.specifications)

    def test_validate_file_not_found(self, sample_ids_path):
        """Test validate raises FileNotFoundError for missing IFC file."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        with pytest.raises(FileNotFoundError):
            validate("/nonexistent/model.ifc", sample_ids_path)

    def test_validate_invalid_extension(self, temp_invalid_extension_file, sample_ids_path):
        """Test validate raises ValueError for invalid extension."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        with pytest.raises(ValueError):
            validate(temp_invalid_extension_file, sample_ids_path)


# =============================================================================
# Critical: Verify failed_entities vs failed_elements
# =============================================================================


class TestFailedEntitiesNotElements:
    """CRITICAL: Verify code uses spec.failed_entities NOT spec.failed_elements.

    This is a common bug mentioned in the spec - the correct attribute is
    spec.failed_entities, not spec.failed_elements.
    """

    def test_validator_code_uses_failed_entities(self):
        """Verify validator.py uses failed_entities, not failed_elements."""
        validator_file = Path(__file__).parent.parent / "src" / "ifc_validator" / "engine" / "validator.py"

        if not validator_file.exists():
            pytest.skip(f"Validator file not found: {validator_file}")

        content = validator_file.read_text()

        # Should contain failed_entities
        assert "failed_entities" in content, "Code must use spec.failed_entities"

        # Should NOT contain failed_elements (except in comments)
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip comments
            if stripped.startswith("#"):
                continue

            # Check for failed_elements in actual code
            if "failed_elements" in line and not stripped.startswith("#"):
                # This is an error unless it's in a comment
                if not any(comment_marker in line.split("failed_elements")[0] for comment_marker in ["#", '"""', "'''"]):
                    pytest.fail(
                        f"Line {i} uses 'failed_elements' instead of 'failed_entities': {line.strip()}"
                    )

    def test_validation_result_uses_correct_attribute(self, sample_fail_ifc_path, sample_ids_path):
        """Test that validation correctly extracts failed entities."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_fail_ifc_path, sample_ids_path)

        # Failing model should have failed entities
        assert result.overall_pass is False

        # Find the failed specification
        failed_specs = [s for s in result.specifications if not s.passed]
        assert len(failed_specs) > 0, "Expected at least one failed specification"

        # Check that failures are populated
        for spec in failed_specs:
            assert spec.failed_count > 0, f"Failed spec '{spec.name}' should have failed_count > 0"
            assert len(spec.failures) > 0, f"Failed spec '{spec.name}' should have failure details"

            # Verify failure details are EntityFailure instances
            for failure in spec.failures:
                assert isinstance(failure, EntityFailure)


# =============================================================================
# Entity Failure Extraction Tests
# =============================================================================


class TestEntityFailureExtraction:
    """Test _extract_entity_failure helper function."""

    def test_extract_entity_failure_with_mock_entity(self):
        """Test extracting failure details from mock entity."""
        mock_entity = MagicMock()
        mock_entity.id.return_value = 123
        mock_entity.is_a.return_value = "IfcWall"
        mock_entity.Name = "Test Wall"
        mock_entity.GlobalId = "abc123"

        failure = _extract_entity_failure(mock_entity)

        assert failure.entity_id == 123
        assert failure.entity_type == "IfcWall"
        assert failure.entity_name == "Test Wall"
        assert failure.global_id == "abc123"

    def test_extract_entity_failure_with_missing_attributes(self):
        """Test extracting failure details from entity without Name/GlobalId."""
        mock_entity = MagicMock(spec=["id", "is_a"])
        mock_entity.id.return_value = 456
        mock_entity.is_a.return_value = "IfcProduct"

        failure = _extract_entity_failure(mock_entity)

        assert failure.entity_id == 456
        assert failure.entity_type == "IfcProduct"
        # Name and GlobalId should be None when not present
        assert failure.entity_name is None
        assert failure.global_id is None

    def test_extract_entity_failure_handles_exception(self):
        """Test that extraction handles exceptions gracefully."""
        mock_entity = MagicMock()
        mock_entity.id.side_effect = Exception("Test error")

        failure = _extract_entity_failure(mock_entity)

        # Should return fallback values
        assert failure.entity_id == 0
        assert failure.entity_type == "Unknown"


# =============================================================================
# Pass Rate Calculation Tests
# =============================================================================


class TestPassRateCalculation:
    """Test pass rate percentage calculation."""

    def test_pass_rate_100_percent(self, sample_ifc_path, sample_ids_path):
        """Test pass rate is 100% when all specs pass."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        if result.overall_pass:
            assert result.pass_rate_percent == 100.0
            assert result.passed_specifications == result.total_specifications

    def test_pass_rate_calculation(self, sample_fail_ifc_path, sample_ids_path):
        """Test pass rate calculation with failures."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_fail_ifc_path, sample_ids_path)

        # Verify pass rate calculation
        expected_rate = (result.passed_specifications / result.total_specifications * 100) if result.total_specifications > 0 else 0.0
        assert abs(result.pass_rate_percent - expected_rate) < 0.1


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_validate_with_string_path(self, sample_ifc_path, sample_ids_path):
        """Test validate accepts string paths."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        # Pass strings instead of Path objects
        result = validate(str(sample_ifc_path), str(sample_ids_path))
        assert isinstance(result, ValidationResult)

    def test_validate_with_path_objects(self, sample_ifc_path, sample_ids_path):
        """Test validate accepts Path objects."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        # Pass Path objects
        result = validate(sample_ifc_path, sample_ids_path)
        assert isinstance(result, ValidationResult)

    def test_specification_with_none_description(self, sample_ifc_path, sample_ids_path):
        """Test handling specifications with None description."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        # Descriptions may be None
        for spec in result.specifications:
            # Should not raise error even if description is None
            assert spec.name is not None  # Name should have default

    def test_overall_pass_false_when_any_spec_fails(self, sample_fail_ifc_path, sample_ids_path):
        """Test overall_pass is False when any specification fails."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_fail_ifc_path, sample_ids_path)

        # If any spec fails, overall_pass should be False
        if result.failed_specifications > 0:
            assert result.overall_pass is False
