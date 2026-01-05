"""Unit tests for the server/ids_validator.py module.

Tests cover:
- IDS file loading and specification count validation
- Complete IFC-IDS validation workflow
- Failed entity extraction with all required fields
- File not found error handling
- ValidationReport structure and field types
- Timing metrics capture
- IDSValidator class functionality
- Report serialization to JSON

Usage:
    pytest test/test_ids_validator.py -v
    pytest test/test_ids_validator.py --cov=server --cov-report=term-missing
"""

import json
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.ids_validator import (
    EntityFailure,
    IDSValidator,
    SpecificationResult,
    ValidationReport,
    report_to_dict,
    validate_ifc_against_ids,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def ifc_path() -> Path:
    """Path to test IFC file.

    Returns the path to the 2786_CLT_model.ifc file in the test directory.
    This is an IFC4X3 model with ~154K entities.
    """
    return Path(__file__).parent / "2786_CLT_model.ifc"


@pytest.fixture
def ids_path() -> Path:
    """Path to test IDS file.

    Returns the path to the NL_BIM_Basis_ILS_v2.ids file in ids-bestanden.
    This IDS file contains 12 specifications.
    """
    return Path(__file__).parent.parent / "ids-bestanden" / "NL_BIM_Basis_ILS_v2.ids"


@pytest.fixture
def validator() -> IDSValidator:
    """IDSValidator instance for testing.

    Returns a fresh IDSValidator instance. The validator is stateless,
    so each test gets an independent instance.
    """
    return IDSValidator()


@pytest.fixture
def nonexistent_ifc_path() -> Path:
    """Path to a non-existent IFC file for error testing."""
    return Path(__file__).parent / "nonexistent_model.ifc"


@pytest.fixture
def nonexistent_ids_path() -> Path:
    """Path to a non-existent IDS file for error testing."""
    return Path(__file__).parent / "nonexistent_spec.ids"


# =============================================================================
# Fixture Verification Tests
# =============================================================================


class TestFixtures:
    """Verify test fixtures are set up correctly."""

    def test_ifc_path_exists(self, ifc_path: Path) -> None:
        """Verify the test IFC file exists."""
        assert ifc_path.exists(), f"Test IFC file not found: {ifc_path}"
        assert ifc_path.suffix.lower() == ".ifc"

    def test_ids_path_exists(self, ids_path: Path) -> None:
        """Verify the test IDS file exists."""
        assert ids_path.exists(), f"Test IDS file not found: {ids_path}"
        assert ids_path.suffix.lower() == ".ids"

    def test_validator_instance(self, validator: IDSValidator) -> None:
        """Verify IDSValidator can be instantiated."""
        assert validator is not None
        assert isinstance(validator, IDSValidator)

    def test_nonexistent_paths_do_not_exist(
        self, nonexistent_ifc_path: Path, nonexistent_ids_path: Path
    ) -> None:
        """Verify nonexistent path fixtures point to non-existing files."""
        assert not nonexistent_ifc_path.exists()
        assert not nonexistent_ids_path.exists()


# =============================================================================
# IDS File Loading Tests
# =============================================================================


class TestIDSFileLoading:
    """Test IDS file loading and specification count."""

    def test_load_ids_file(self, ids_path: Path) -> None:
        """Test that IDS files load correctly with correct specification count.

        This test verifies:
        - IDS file can be loaded using ifctester.ids.open()
        - The NL_BIM_Basis_ILS_v2.ids file contains exactly 12 specifications
        - Specifications can be iterated over

        Acceptance Criteria:
        - Test loads IDS file using ifctester.ids.open()
        - Asserts specification count is 12
        - Test passes with valid IDS file
        """
        from ifctester import ids

        # Load IDS file using ifctester
        ids_file = ids.open(str(ids_path))

        # Verify IDS file was loaded successfully
        assert ids_file is not None, "IDS file should load successfully"

        # Verify specifications attribute exists
        assert hasattr(ids_file, "specifications"), "IDS file should have specifications attribute"

        # Verify specification count is exactly 12 for NL_BIM_Basis_ILS_v2.ids
        spec_count = len(ids_file.specifications)
        assert spec_count == 12, (
            f"NL_BIM_Basis_ILS_v2.ids should contain 12 specifications, "
            f"got {spec_count}"
        )

    def test_ids_specifications_have_names(self, ids_path: Path) -> None:
        """Test that each specification in the IDS file has a name.

        This verifies the IDS file is properly structured with named specifications
        that can be used for validation reporting.
        """
        from ifctester import ids

        ids_file = ids.open(str(ids_path))

        for i, spec in enumerate(ids_file.specifications):
            assert hasattr(spec, "name"), f"Specification {i} should have 'name' attribute"
            assert spec.name is not None, f"Specification {i} name should not be None"
            assert len(spec.name) > 0, f"Specification {i} name should not be empty"


# =============================================================================
# Validation Workflow Tests
# =============================================================================


class TestValidationWorkflow:
    """Test complete validation workflow and ValidationReport structure."""

    def test_validate_success(self, ifc_path: Path, ids_path: Path) -> None:
        """Test complete validation workflow returns ValidationReport with correct structure.

        This test verifies:
        - validate_ifc_against_ids() successfully validates IFC against IDS
        - Returns a ValidationReport instance
        - Report contains exactly 12 specifications (for NL_BIM_Basis_ILS_v2.ids)
        - All aggregate fields are populated with expected types/values

        Acceptance Criteria:
        - Calls validate_ifc_against_ids with valid files
        - Asserts report is ValidationReport instance
        - Asserts total_specifications == 12
        - Asserts all aggregate fields populated
        """
        # Run validation with valid files
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Verify return type is ValidationReport
        assert isinstance(report, ValidationReport), (
            f"Expected ValidationReport instance, got {type(report).__name__}"
        )

        # Verify validation completed successfully
        assert report.success is True, (
            f"Validation should succeed, error: {report.error}"
        )
        assert report.error is None, (
            f"Error should be None on success, got: {report.error}"
        )

        # Verify specification count is exactly 12 for NL_BIM_Basis_ILS_v2.ids
        assert report.total_specifications == 12, (
            f"Expected 12 specifications, got {report.total_specifications}"
        )

        # Verify aggregate counts are populated and consistent
        assert report.passed_specifications >= 0, "passed_specifications should be >= 0"
        assert report.failed_specifications >= 0, "failed_specifications should be >= 0"
        assert report.passed_specifications + report.failed_specifications == report.total_specifications, (
            f"passed ({report.passed_specifications}) + failed ({report.failed_specifications}) "
            f"should equal total ({report.total_specifications})"
        )

        # Verify pass rate is calculated correctly
        expected_pass_rate = (report.passed_specifications / report.total_specifications * 100)
        assert abs(report.pass_rate_percent - expected_pass_rate) < 0.2, (
            f"Pass rate {report.pass_rate_percent}% doesn't match expected "
            f"{expected_pass_rate:.1f}%"
        )
        assert 0.0 <= report.pass_rate_percent <= 100.0, (
            f"Pass rate should be between 0-100, got {report.pass_rate_percent}"
        )

        # Verify IFC file metadata is populated
        assert report.ifc_file is not None and len(report.ifc_file) > 0, (
            "ifc_file should be populated"
        )
        assert report.ifc_schema is not None and len(report.ifc_schema) > 0, (
            "ifc_schema should be populated"
        )
        assert report.ifc_entity_count > 0, (
            f"ifc_entity_count should be > 0 for a valid IFC file, got {report.ifc_entity_count}"
        )

        # Verify IDS file metadata is populated
        assert report.ids_file is not None and len(report.ids_file) > 0, (
            "ids_file should be populated"
        )

        # Verify timing metrics are captured
        assert report.validation_time_seconds >= 0, (
            f"validation_time_seconds should be >= 0, got {report.validation_time_seconds}"
        )

        # Verify timestamp is populated (ISO format string)
        assert report.timestamp is not None and len(report.timestamp) > 0, (
            "timestamp should be populated"
        )

        # Verify specifications list is populated with correct length
        assert isinstance(report.specifications, list), (
            f"specifications should be a list, got {type(report.specifications).__name__}"
        )
        assert len(report.specifications) == report.total_specifications, (
            f"specifications list length ({len(report.specifications)}) should match "
            f"total_specifications ({report.total_specifications})"
        )

        # Verify each specification result is properly structured
        for i, spec in enumerate(report.specifications):
            assert isinstance(spec, SpecificationResult), (
                f"Specification {i} should be SpecificationResult, got {type(spec).__name__}"
            )
            assert spec.name is not None and len(spec.name) > 0, (
                f"Specification {i} name should be populated"
            )
            assert isinstance(spec.passed, bool), (
                f"Specification {i} passed should be bool, got {type(spec.passed).__name__}"
            )
            assert spec.applicable_count >= 0, (
                f"Specification {i} applicable_count should be >= 0"
            )
            assert spec.passed_count >= 0, (
                f"Specification {i} passed_count should be >= 0"
            )
            assert spec.failed_count >= 0, (
                f"Specification {i} failed_count should be >= 0"
            )
            assert isinstance(spec.failures, list), (
                f"Specification {i} failures should be a list"
            )


# =============================================================================
# Failed Entity Extraction Tests
# =============================================================================


class TestFailedEntityExtraction:
    """Test that failed entities are extracted with all required fields."""

    def test_failed_entities_extraction(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that failed entities are extracted with all required fields.

        This test verifies:
        - Validation that has failures produces EntityFailure objects
        - Failed specifications have populated failures lists
        - Each EntityFailure has all required fields:
          - entity_id (int)
          - entity_type (str)
          - entity_name (Optional[str])
          - global_id (Optional[str])

        Acceptance Criteria:
        - Runs validation that has failures
        - Finds a specification with failed_count > 0
        - Asserts failures list is populated
        - Asserts each failure has entity_id, entity_type
        - Asserts entity_name and global_id are present (may be None)
        """
        # Run validation - we know NL_BIM_Basis_ILS_v2.ids has failing specs
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Verify validation completed successfully
        assert report.success is True, f"Validation should succeed, error: {report.error}"

        # Find specifications with failures
        specs_with_failures = [
            spec for spec in report.specifications
            if spec.failed_count > 0 and len(spec.failures) > 0
        ]

        # Verify we have at least one specification with failures
        # (NL_BIM_Basis_ILS_v2.ids is known to have 8 failing specs)
        assert len(specs_with_failures) > 0, (
            "Expected at least one specification with failures to test entity extraction. "
            f"Failed specs: {report.failed_specifications}, "
            f"specs with failure details: {len(specs_with_failures)}"
        )

        # Test each specification with failures
        for spec in specs_with_failures:
            # Verify failures list is populated
            assert len(spec.failures) > 0, (
                f"Specification '{spec.name}' has failed_count={spec.failed_count} "
                f"but empty failures list"
            )

            # Verify failure count matches list length
            assert spec.failed_count == len(spec.failures), (
                f"Specification '{spec.name}' failed_count ({spec.failed_count}) "
                f"doesn't match failures list length ({len(spec.failures)})"
            )

            # Check each failed entity has all required fields
            for i, failure in enumerate(spec.failures):
                # Verify failure is an EntityFailure instance
                assert isinstance(failure, EntityFailure), (
                    f"Failure {i} in '{spec.name}' should be EntityFailure, "
                    f"got {type(failure).__name__}"
                )

                # Verify entity_id is an integer
                assert isinstance(failure.entity_id, int), (
                    f"Failure {i} in '{spec.name}': entity_id should be int, "
                    f"got {type(failure.entity_id).__name__}"
                )
                # entity_id should be positive (valid IFC instance ID)
                assert failure.entity_id > 0, (
                    f"Failure {i} in '{spec.name}': entity_id should be > 0, "
                    f"got {failure.entity_id}"
                )

                # Verify entity_type is a non-empty string
                assert isinstance(failure.entity_type, str), (
                    f"Failure {i} in '{spec.name}': entity_type should be str, "
                    f"got {type(failure.entity_type).__name__}"
                )
                assert len(failure.entity_type) > 0, (
                    f"Failure {i} in '{spec.name}': entity_type should not be empty"
                )

                # Verify entity_name is present (can be str or None)
                assert failure.entity_name is None or isinstance(failure.entity_name, str), (
                    f"Failure {i} in '{spec.name}': entity_name should be str or None, "
                    f"got {type(failure.entity_name).__name__}"
                )

                # Verify global_id is present (can be str or None)
                assert failure.global_id is None or isinstance(failure.global_id, str), (
                    f"Failure {i} in '{spec.name}': global_id should be str or None, "
                    f"got {type(failure.global_id).__name__}"
                )

    def test_failed_entity_has_valid_ifc_type(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that extracted entity_type is a valid IFC type name.

        IFC entity types follow a naming convention (e.g., IfcWall, IfcDoor).
        This test verifies extracted types follow this pattern.
        """
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Find first failure to inspect
        for spec in report.specifications:
            if spec.failures:
                failure = spec.failures[0]

                # IFC type names typically start with "Ifc" or are uppercase
                # At minimum, they should be non-empty alphanumeric strings
                assert failure.entity_type.isalnum() or "_" in failure.entity_type, (
                    f"entity_type '{failure.entity_type}' should be alphanumeric"
                )
                return  # Test passed with one failure

        # If no failures found, skip with informative message
        pytest.skip("No failures found to test entity_type format")

    def test_failed_entities_global_id_format(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that GlobalId values follow IFC GUID format when present.

        IFC GlobalId is a 22-character compressed GUID. This test verifies
        that when global_id is present, it has the expected format.
        """
        report = validate_ifc_against_ids(ifc_path, ids_path)

        found_global_id = False
        for spec in report.specifications:
            for failure in spec.failures:
                if failure.global_id is not None:
                    found_global_id = True
                    # IFC GlobalId is a 22-character encoded GUID
                    assert len(failure.global_id) == 22, (
                        f"global_id '{failure.global_id}' should be 22 characters "
                        f"(IFC GUID format), got {len(failure.global_id)}"
                    )

        if not found_global_id:
            pytest.skip("No failures with GlobalId found to test format")


# =============================================================================
# File Not Found Error Tests
# =============================================================================


class TestFileNotFoundError:
    """Test that FileNotFoundError is raised with clear messages for missing files."""

    def test_missing_ifc_file_raises_file_not_found_error(
        self, nonexistent_ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that missing IFC file raises FileNotFoundError with path in message.

        This test verifies:
        - FileNotFoundError is raised when IFC file doesn't exist
        - The error message includes the file path for debugging

        Acceptance Criteria:
        - Tests missing IFC file raises FileNotFoundError
        - Error message includes file path
        """
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_ifc_against_ids(nonexistent_ifc_path, ids_path)

        # Verify error message includes the missing file path
        error_message = str(exc_info.value)
        assert "IFC file not found" in error_message, (
            f"Error message should indicate IFC file not found, got: {error_message}"
        )
        assert str(nonexistent_ifc_path) in error_message or nonexistent_ifc_path.name in error_message, (
            f"Error message should include file path, got: {error_message}"
        )

    def test_missing_ids_file_raises_file_not_found_error(
        self, ifc_path: Path, nonexistent_ids_path: Path
    ) -> None:
        """Test that missing IDS file raises FileNotFoundError with path in message.

        This test verifies:
        - FileNotFoundError is raised when IDS file doesn't exist
        - The error message includes the file path for debugging

        Acceptance Criteria:
        - Tests missing IDS file raises FileNotFoundError
        - Error message includes file path
        """
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_ifc_against_ids(ifc_path, nonexistent_ids_path)

        # Verify error message includes the missing file path
        error_message = str(exc_info.value)
        assert "IDS file not found" in error_message, (
            f"Error message should indicate IDS file not found, got: {error_message}"
        )
        assert str(nonexistent_ids_path) in error_message or nonexistent_ids_path.name in error_message, (
            f"Error message should include file path, got: {error_message}"
        )

    def test_both_files_missing_raises_ifc_error_first(
        self, nonexistent_ifc_path: Path, nonexistent_ids_path: Path
    ) -> None:
        """Test that when both files are missing, IFC file error is raised first.

        The validation function checks IFC file existence before IDS file,
        so when both are missing, the IFC error should be raised first.
        This tests the implementation order of validation checks.
        """
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_ifc_against_ids(nonexistent_ifc_path, nonexistent_ids_path)

        error_message = str(exc_info.value)
        # Should get IFC error first since it's checked first
        assert "IFC" in error_message, (
            f"When both files missing, IFC error should be raised first, got: {error_message}"
        )

    def test_validator_class_missing_ifc_file_raises_error(
        self, validator: IDSValidator, nonexistent_ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that IDSValidator.validate() also raises FileNotFoundError for missing IFC.

        This verifies the class-based interface behaves consistently with the
        standalone function for error handling.
        """
        with pytest.raises(FileNotFoundError) as exc_info:
            validator.validate(nonexistent_ifc_path, ids_path)

        error_message = str(exc_info.value)
        assert "IFC file not found" in error_message

    def test_validator_class_missing_ids_file_raises_error(
        self, validator: IDSValidator, ifc_path: Path, nonexistent_ids_path: Path
    ) -> None:
        """Test that IDSValidator.validate() also raises FileNotFoundError for missing IDS.

        This verifies the class-based interface behaves consistently with the
        standalone function for error handling.
        """
        with pytest.raises(FileNotFoundError) as exc_info:
            validator.validate(ifc_path, nonexistent_ids_path)

        error_message = str(exc_info.value)
        assert "IDS file not found" in error_message


# =============================================================================
# ValidationReport Structure Tests
# =============================================================================


class TestValidationReportStructure:
    """Test that ValidationReport has all required fields with correct types."""

    def test_validation_report_structure(self, ifc_path: Path, ids_path: Path) -> None:
        """Test ValidationReport has all required fields with correct types.

        This test verifies:
        - All 14 fields are present on ValidationReport
        - timestamp is a string in ISO format
        - ifc_file and ids_file are strings
        - All count fields are integers
        - pass_rate_percent and validation_time_seconds are floats
        - specifications is a list of SpecificationResult objects
        - success is a boolean and error is Optional[str]

        Acceptance Criteria:
        - Asserts timestamp is string in ISO format
        - Asserts ifc_file and ids_file are strings
        - Asserts counts are integers
        - Asserts pass_rate_percent is float
        - Asserts specifications is list
        """
        from datetime import datetime

        # Run validation to get a real report
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Verify report is ValidationReport instance
        assert isinstance(report, ValidationReport), (
            f"Expected ValidationReport instance, got {type(report).__name__}"
        )

        # ===== Test timestamp field =====
        # timestamp should be a string in ISO format
        assert isinstance(report.timestamp, str), (
            f"timestamp should be str, got {type(report.timestamp).__name__}"
        )
        assert len(report.timestamp) > 0, "timestamp should not be empty"

        # Verify timestamp is valid ISO format by parsing it
        try:
            parsed_timestamp = datetime.fromisoformat(report.timestamp)
            assert parsed_timestamp is not None
        except ValueError as e:
            pytest.fail(f"timestamp '{report.timestamp}' is not valid ISO format: {e}")

        # ===== Test IFC file metadata fields =====
        # ifc_file should be a non-empty string
        assert isinstance(report.ifc_file, str), (
            f"ifc_file should be str, got {type(report.ifc_file).__name__}"
        )
        assert len(report.ifc_file) > 0, "ifc_file should not be empty"

        # ifc_schema should be a non-empty string
        assert isinstance(report.ifc_schema, str), (
            f"ifc_schema should be str, got {type(report.ifc_schema).__name__}"
        )
        assert len(report.ifc_schema) > 0, "ifc_schema should not be empty"

        # ifc_entity_count should be a non-negative integer
        assert isinstance(report.ifc_entity_count, int), (
            f"ifc_entity_count should be int, got {type(report.ifc_entity_count).__name__}"
        )
        assert report.ifc_entity_count >= 0, (
            f"ifc_entity_count should be >= 0, got {report.ifc_entity_count}"
        )

        # ===== Test IDS file metadata fields =====
        # ids_file should be a non-empty string
        assert isinstance(report.ids_file, str), (
            f"ids_file should be str, got {type(report.ids_file).__name__}"
        )
        assert len(report.ids_file) > 0, "ids_file should not be empty"

        # ids_title should be str or None
        assert report.ids_title is None or isinstance(report.ids_title, str), (
            f"ids_title should be str or None, got {type(report.ids_title).__name__}"
        )

        # ===== Test timing field =====
        # validation_time_seconds should be a non-negative float
        assert isinstance(report.validation_time_seconds, float), (
            f"validation_time_seconds should be float, got {type(report.validation_time_seconds).__name__}"
        )
        assert report.validation_time_seconds >= 0.0, (
            f"validation_time_seconds should be >= 0, got {report.validation_time_seconds}"
        )

        # ===== Test specification count fields =====
        # total_specifications should be a non-negative integer
        assert isinstance(report.total_specifications, int), (
            f"total_specifications should be int, got {type(report.total_specifications).__name__}"
        )
        assert report.total_specifications >= 0, (
            f"total_specifications should be >= 0, got {report.total_specifications}"
        )

        # passed_specifications should be a non-negative integer
        assert isinstance(report.passed_specifications, int), (
            f"passed_specifications should be int, got {type(report.passed_specifications).__name__}"
        )
        assert report.passed_specifications >= 0, (
            f"passed_specifications should be >= 0, got {report.passed_specifications}"
        )

        # failed_specifications should be a non-negative integer
        assert isinstance(report.failed_specifications, int), (
            f"failed_specifications should be int, got {type(report.failed_specifications).__name__}"
        )
        assert report.failed_specifications >= 0, (
            f"failed_specifications should be >= 0, got {report.failed_specifications}"
        )

        # ===== Test pass rate field =====
        # pass_rate_percent should be a float between 0 and 100
        assert isinstance(report.pass_rate_percent, float), (
            f"pass_rate_percent should be float, got {type(report.pass_rate_percent).__name__}"
        )
        assert 0.0 <= report.pass_rate_percent <= 100.0, (
            f"pass_rate_percent should be between 0-100, got {report.pass_rate_percent}"
        )

        # ===== Test specifications list field =====
        # specifications should be a list
        assert isinstance(report.specifications, list), (
            f"specifications should be list, got {type(report.specifications).__name__}"
        )

        # Each item in specifications should be a SpecificationResult
        for i, spec in enumerate(report.specifications):
            assert isinstance(spec, SpecificationResult), (
                f"specifications[{i}] should be SpecificationResult, "
                f"got {type(spec).__name__}"
            )

        # ===== Test success/error fields =====
        # success should be a boolean
        assert isinstance(report.success, bool), (
            f"success should be bool, got {type(report.success).__name__}"
        )

        # error should be str or None
        assert report.error is None or isinstance(report.error, str), (
            f"error should be str or None, got {type(report.error).__name__}"
        )

    def test_validation_report_field_count(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that ValidationReport has exactly 14 fields.

        This verifies the dataclass hasn't been modified unexpectedly.
        """
        from dataclasses import fields

        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Get all field names from the dataclass
        field_names = [f.name for f in fields(report)]

        # Expected 14 fields as documented in spec
        expected_fields = [
            "timestamp",
            "ifc_file",
            "ifc_schema",
            "ifc_entity_count",
            "ids_file",
            "ids_title",
            "validation_time_seconds",
            "total_specifications",
            "passed_specifications",
            "failed_specifications",
            "pass_rate_percent",
            "specifications",
            "success",
            "error",
        ]

        assert len(field_names) == 14, (
            f"ValidationReport should have 14 fields, got {len(field_names)}: {field_names}"
        )

        # Verify all expected fields are present
        for expected_field in expected_fields:
            assert expected_field in field_names, (
                f"ValidationReport missing expected field: {expected_field}"
            )

    def test_specification_result_field_count(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that SpecificationResult has exactly 7 fields.

        This verifies the dataclass structure matches the spec.
        """
        from dataclasses import fields

        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Get a SpecificationResult to inspect
        assert len(report.specifications) > 0, "Need at least one spec to test"
        spec = report.specifications[0]

        # Get all field names from the dataclass
        field_names = [f.name for f in fields(spec)]

        # Expected 7 fields as documented in spec
        expected_fields = [
            "name",
            "description",
            "passed",
            "applicable_count",
            "passed_count",
            "failed_count",
            "failures",
        ]

        assert len(field_names) == 7, (
            f"SpecificationResult should have 7 fields, got {len(field_names)}: {field_names}"
        )

        # Verify all expected fields are present
        for expected_field in expected_fields:
            assert expected_field in field_names, (
                f"SpecificationResult missing expected field: {expected_field}"
            )

    def test_entity_failure_field_count(self) -> None:
        """Test that EntityFailure has exactly 4 fields.

        This verifies the dataclass structure matches the spec.
        """
        from dataclasses import fields

        # Create a sample EntityFailure to inspect fields
        sample_failure = EntityFailure(
            entity_id=1,
            entity_type="IfcWall",
            entity_name="Test Wall",
            global_id="1234567890123456789012",
        )

        # Get all field names from the dataclass
        field_names = [f.name for f in fields(sample_failure)]

        # Expected 4 fields as documented in spec
        expected_fields = ["entity_id", "entity_type", "entity_name", "global_id"]

        assert len(field_names) == 4, (
            f"EntityFailure should have 4 fields, got {len(field_names)}: {field_names}"
        )

        # Verify all expected fields are present
        for expected_field in expected_fields:
            assert expected_field in field_names, (
                f"EntityFailure missing expected field: {expected_field}"
            )


# =============================================================================
# IDSValidator Class Tests
# =============================================================================


class TestIDSValidatorClass:
    """Test IDSValidator class instantiation, validate method, and get_capabilities."""

    def test_ids_validator_can_be_instantiated(self) -> None:
        """Test that IDSValidator can be instantiated without arguments.

        This test verifies:
        - IDSValidator class can be instantiated
        - No constructor arguments are required
        - Instance is a valid IDSValidator object

        Acceptance Criteria:
        - IDSValidator can be instantiated
        """
        # Instantiate the validator
        validator = IDSValidator()

        # Verify the instance is created
        assert validator is not None, "IDSValidator should instantiate successfully"

        # Verify it's the correct type
        assert isinstance(validator, IDSValidator), (
            f"Expected IDSValidator instance, got {type(validator).__name__}"
        )

    def test_ids_validator_validate_returns_validation_report(
        self, validator: IDSValidator, ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that IDSValidator.validate() returns a ValidationReport.

        This test verifies:
        - validate() method exists on IDSValidator
        - validate() returns a ValidationReport instance
        - The report is successfully populated with validation results

        Acceptance Criteria:
        - validate() method returns ValidationReport
        """
        # Run validation using the class-based interface
        report = validator.validate(ifc_path, ids_path)

        # Verify return type is ValidationReport
        assert isinstance(report, ValidationReport), (
            f"validate() should return ValidationReport, got {type(report).__name__}"
        )

        # Verify the validation completed successfully
        assert report.success is True, (
            f"Validation should succeed, error: {report.error}"
        )

    def test_ids_validator_validate_matches_function(
        self, validator: IDSValidator, ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that IDSValidator.validate() produces same results as function.

        This verifies the class-based interface produces consistent results
        with the standalone validate_ifc_against_ids() function.
        """
        # Run validation using both interfaces
        class_report = validator.validate(ifc_path, ids_path)
        func_report = validate_ifc_against_ids(ifc_path, ids_path)

        # Verify key metrics match
        assert class_report.total_specifications == func_report.total_specifications, (
            f"total_specifications mismatch: class={class_report.total_specifications}, "
            f"func={func_report.total_specifications}"
        )
        assert class_report.passed_specifications == func_report.passed_specifications, (
            f"passed_specifications mismatch: class={class_report.passed_specifications}, "
            f"func={func_report.passed_specifications}"
        )
        assert class_report.failed_specifications == func_report.failed_specifications, (
            f"failed_specifications mismatch: class={class_report.failed_specifications}, "
            f"func={func_report.failed_specifications}"
        )

        # Verify metadata matches
        assert class_report.ifc_file == func_report.ifc_file
        assert class_report.ids_file == func_report.ids_file
        assert class_report.ifc_schema == func_report.ifc_schema

    def test_ids_validator_validate_report_has_all_fields(
        self, validator: IDSValidator, ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that ValidationReport from validate() has all required fields.

        This ensures the class method produces a complete report with all fields.
        """
        report = validator.validate(ifc_path, ids_path)

        # Verify all 14 required fields are present and populated
        assert hasattr(report, "timestamp") and report.timestamp
        assert hasattr(report, "ifc_file") and report.ifc_file
        assert hasattr(report, "ifc_schema") and report.ifc_schema
        assert hasattr(report, "ifc_entity_count") and report.ifc_entity_count >= 0
        assert hasattr(report, "ids_file") and report.ids_file
        assert hasattr(report, "ids_title")  # Can be None
        assert hasattr(report, "validation_time_seconds")
        assert hasattr(report, "total_specifications") and report.total_specifications >= 0
        assert hasattr(report, "passed_specifications") and report.passed_specifications >= 0
        assert hasattr(report, "failed_specifications") and report.failed_specifications >= 0
        assert hasattr(report, "pass_rate_percent")
        assert hasattr(report, "specifications") and isinstance(report.specifications, list)
        assert hasattr(report, "success") and isinstance(report.success, bool)
        assert hasattr(report, "error")  # Can be None

    def test_get_capabilities_returns_dict(self, validator: IDSValidator) -> None:
        """Test that get_capabilities() returns a dictionary.

        This test verifies:
        - get_capabilities() method exists on IDSValidator
        - Returns a dict type

        Acceptance Criteria:
        - get_capabilities() returns dict with expected keys
        """
        # Get capabilities
        capabilities = validator.get_capabilities()

        # Verify return type is dict
        assert isinstance(capabilities, dict), (
            f"get_capabilities() should return dict, got {type(capabilities).__name__}"
        )

    def test_get_capabilities_has_expected_keys(self, validator: IDSValidator) -> None:
        """Test that get_capabilities() returns dict with all expected keys.

        This verifies the capabilities dict includes:
        - ifcopenshell_version
        - ifctester_version
        - supported_ids_versions
        - validation_available

        Acceptance Criteria:
        - get_capabilities() returns dict with expected keys
        """
        capabilities = validator.get_capabilities()

        # Define expected keys
        expected_keys = [
            "ifcopenshell_version",
            "ifctester_version",
            "supported_ids_versions",
            "validation_available",
        ]

        # Verify all expected keys are present
        for key in expected_keys:
            assert key in capabilities, (
                f"get_capabilities() should include '{key}' key, "
                f"available keys: {list(capabilities.keys())}"
            )

    def test_get_capabilities_values_have_correct_types(self, validator: IDSValidator) -> None:
        """Test that get_capabilities() values have correct types.

        This verifies:
        - ifcopenshell_version is a string
        - ifctester_version is a string
        - supported_ids_versions is a list
        - validation_available is a boolean
        """
        capabilities = validator.get_capabilities()

        # Verify ifcopenshell_version is string
        assert isinstance(capabilities["ifcopenshell_version"], str), (
            f"ifcopenshell_version should be str, "
            f"got {type(capabilities['ifcopenshell_version']).__name__}"
        )

        # Verify ifctester_version is string
        assert isinstance(capabilities["ifctester_version"], str), (
            f"ifctester_version should be str, "
            f"got {type(capabilities['ifctester_version']).__name__}"
        )

        # Verify supported_ids_versions is list
        assert isinstance(capabilities["supported_ids_versions"], list), (
            f"supported_ids_versions should be list, "
            f"got {type(capabilities['supported_ids_versions']).__name__}"
        )

        # Verify validation_available is boolean
        assert isinstance(capabilities["validation_available"], bool), (
            f"validation_available should be bool, "
            f"got {type(capabilities['validation_available']).__name__}"
        )

    def test_get_capabilities_validation_available_is_true(self, validator: IDSValidator) -> None:
        """Test that validation_available capability is True.

        The IDS validator module should always report that validation is available.
        """
        capabilities = validator.get_capabilities()

        assert capabilities["validation_available"] is True, (
            "validation_available should be True for IDS validator"
        )

    def test_get_capabilities_supported_ids_versions_not_empty(
        self, validator: IDSValidator
    ) -> None:
        """Test that supported_ids_versions contains at least one version.

        The validator should support at least IDS version 1.0.
        """
        capabilities = validator.get_capabilities()

        assert len(capabilities["supported_ids_versions"]) > 0, (
            "supported_ids_versions should not be empty"
        )

        # Verify "1.0" is in supported versions
        assert "1.0" in capabilities["supported_ids_versions"], (
            f"supported_ids_versions should include '1.0', "
            f"got {capabilities['supported_ids_versions']}"
        )

    def test_multiple_validators_are_independent(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that multiple IDSValidator instances work independently.

        This ensures the validator is stateless and multiple instances
        can be used concurrently without interference.
        """
        # Create two separate validators
        validator1 = IDSValidator()
        validator2 = IDSValidator()

        # Run validation on both
        report1 = validator1.validate(ifc_path, ids_path)
        report2 = validator2.validate(ifc_path, ids_path)

        # Both should succeed independently
        assert report1.success is True
        assert report2.success is True

        # Results should be consistent
        assert report1.total_specifications == report2.total_specifications
        assert report1.passed_specifications == report2.passed_specifications


# =============================================================================
# Timing Metrics Tests
# =============================================================================


class TestTimingMetrics:
    """Test that validation timing metrics are captured correctly."""

    def test_timing_metrics(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that validation_time_seconds is captured and is greater than 0.

        This test verifies:
        - validation_time_seconds is a float
        - validation_time_seconds is strictly greater than 0 (validation takes time)
        - The validation actually performs work (not returning a cached/instant result)

        Acceptance Criteria:
        - Runs validation and checks validation_time_seconds
        - Asserts validation_time_seconds > 0
        - Asserts validation_time_seconds is float
        """
        # Run validation to get timing metrics
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Verify validation completed successfully
        assert report.success is True, f"Validation should succeed, error: {report.error}"

        # Verify validation_time_seconds is a float
        assert isinstance(report.validation_time_seconds, float), (
            f"validation_time_seconds should be float, "
            f"got {type(report.validation_time_seconds).__name__}"
        )

        # Verify validation_time_seconds is strictly greater than 0
        # Validation of a real IFC file against IDS specs takes measurable time
        assert report.validation_time_seconds > 0, (
            f"validation_time_seconds should be > 0 (validation takes time), "
            f"got {report.validation_time_seconds}"
        )

    def test_timing_is_reasonable(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that validation time is within reasonable bounds.

        This test verifies validation doesn't take an unreasonably long time
        or return an implausibly small time value.

        The test file (2786_CLT_model.ifc, ~6.87 MB) should validate in:
        - More than 0.001 seconds (can't be instant)
        - Less than 60 seconds (should be reasonably fast)
        """
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Validation should take more than 1ms (real work is being done)
        assert report.validation_time_seconds > 0.001, (
            f"validation_time_seconds should be > 0.001s (validation takes real time), "
            f"got {report.validation_time_seconds}s"
        )

        # Validation should complete in less than 60 seconds for test file
        assert report.validation_time_seconds < 60.0, (
            f"validation_time_seconds should be < 60s for test file, "
            f"got {report.validation_time_seconds}s - this may indicate a performance issue"
        )

    def test_timing_precision(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that timing has sufficient precision.

        This verifies the timing mechanism captures sub-second precision,
        which is expected from time.time() based measurements.
        """
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # The validation time should have decimal precision
        # (i.e., not be a whole number like 0.0, 1.0, 2.0)
        # This verifies we're using a precision timer, not just second-counting
        time_str = f"{report.validation_time_seconds:.10f}"

        # Check that there are non-zero digits after the decimal point
        decimal_part = time_str.split(".")[1]
        has_precision = any(c != "0" for c in decimal_part)

        assert has_precision, (
            f"validation_time_seconds should have sub-second precision, "
            f"got {report.validation_time_seconds} which appears to be a whole number"
        )


# =============================================================================
# Report Serialization Tests
# =============================================================================


class TestReportSerialization:
    """Test that ValidationReport can be converted to dict and serialized to JSON."""

    def test_report_to_dict_returns_dict(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that report_to_dict() returns a valid dictionary.

        This test verifies:
        - report_to_dict() function exists and is callable
        - Returns a dict type when passed a ValidationReport

        Acceptance Criteria:
        - report_to_dict() returns valid dict
        """
        # Run validation to get a real report
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Convert report to dict
        result = report_to_dict(report)

        # Verify return type is dict
        assert isinstance(result, dict), (
            f"report_to_dict() should return dict, got {type(result).__name__}"
        )

    def test_report_to_dict_json_serializable(self, ifc_path: Path, ids_path: Path) -> None:
        """Test that the dict from report_to_dict() can be serialized to JSON.

        This test verifies:
        - The dict returned by report_to_dict() can be passed to json.dumps()
        - JSON serialization completes without errors
        - The resulting JSON is a non-empty string

        Acceptance Criteria:
        - json.dumps() succeeds on result
        """
        # Run validation to get a real report
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Convert report to dict
        report_dict = report_to_dict(report)

        # Verify JSON serialization succeeds
        try:
            json_str = json.dumps(report_dict)
        except (TypeError, ValueError) as e:
            pytest.fail(f"json.dumps() failed on report_to_dict result: {e}")

        # Verify we got a non-empty JSON string
        assert isinstance(json_str, str), (
            f"json.dumps() should return str, got {type(json_str).__name__}"
        )
        assert len(json_str) > 0, "JSON string should not be empty"

    def test_report_to_dict_nested_structures_converted(
        self, ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that all nested dataclass structures are properly converted to dicts.

        This test verifies:
        - The specifications field is a list of dicts (not SpecificationResult objects)
        - Each specification's failures field is a list of dicts (not EntityFailure objects)
        - All nested dataclasses are recursively converted

        Acceptance Criteria:
        - All nested structures properly converted
        """
        # Run validation to get a real report
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Convert report to dict
        report_dict = report_to_dict(report)

        # Verify specifications is a list
        assert "specifications" in report_dict, (
            "report_dict should have 'specifications' key"
        )
        assert isinstance(report_dict["specifications"], list), (
            f"specifications should be list, got {type(report_dict['specifications']).__name__}"
        )

        # Verify each specification is a dict (not SpecificationResult)
        for i, spec in enumerate(report_dict["specifications"]):
            assert isinstance(spec, dict), (
                f"specifications[{i}] should be dict, got {type(spec).__name__}"
            )

            # Verify spec has expected keys
            expected_spec_keys = [
                "name",
                "description",
                "passed",
                "applicable_count",
                "passed_count",
                "failed_count",
                "failures",
            ]
            for key in expected_spec_keys:
                assert key in spec, (
                    f"specifications[{i}] should have '{key}' key, "
                    f"available keys: {list(spec.keys())}"
                )

            # Verify failures is a list of dicts (not EntityFailure objects)
            assert isinstance(spec["failures"], list), (
                f"specifications[{i}]['failures'] should be list, "
                f"got {type(spec['failures']).__name__}"
            )

            # Check each failure is a dict with expected keys
            for j, failure in enumerate(spec["failures"]):
                assert isinstance(failure, dict), (
                    f"specifications[{i}]['failures'][{j}] should be dict, "
                    f"got {type(failure).__name__}"
                )

                # Verify failure has expected keys
                expected_failure_keys = [
                    "entity_id",
                    "entity_type",
                    "entity_name",
                    "global_id",
                ]
                for key in expected_failure_keys:
                    assert key in failure, (
                        f"specifications[{i}]['failures'][{j}] should have '{key}' key, "
                        f"available keys: {list(failure.keys())}"
                    )

    def test_report_to_dict_preserves_all_fields(
        self, ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that all ValidationReport fields are preserved in the dict.

        This verifies that report_to_dict() doesn't lose any data from the
        original ValidationReport dataclass.
        """
        # Run validation to get a real report
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Convert report to dict
        report_dict = report_to_dict(report)

        # Verify all 14 expected fields are present in the dict
        expected_fields = [
            "timestamp",
            "ifc_file",
            "ifc_schema",
            "ifc_entity_count",
            "ids_file",
            "ids_title",
            "validation_time_seconds",
            "total_specifications",
            "passed_specifications",
            "failed_specifications",
            "pass_rate_percent",
            "specifications",
            "success",
            "error",
        ]

        for field in expected_fields:
            assert field in report_dict, (
                f"report_dict should have '{field}' key, "
                f"available keys: {list(report_dict.keys())}"
            )

        # Verify values match original report
        assert report_dict["timestamp"] == report.timestamp
        assert report_dict["ifc_file"] == report.ifc_file
        assert report_dict["ifc_schema"] == report.ifc_schema
        assert report_dict["ifc_entity_count"] == report.ifc_entity_count
        assert report_dict["ids_file"] == report.ids_file
        assert report_dict["ids_title"] == report.ids_title
        assert report_dict["validation_time_seconds"] == report.validation_time_seconds
        assert report_dict["total_specifications"] == report.total_specifications
        assert report_dict["passed_specifications"] == report.passed_specifications
        assert report_dict["failed_specifications"] == report.failed_specifications
        assert report_dict["pass_rate_percent"] == report.pass_rate_percent
        assert report_dict["success"] == report.success
        assert report_dict["error"] == report.error

    def test_report_to_dict_json_roundtrip(
        self, ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that JSON can be parsed back into a dict with correct values.

        This tests the full serialization roundtrip:
        ValidationReport -> dict -> JSON string -> dict

        The final dict should have the same values as the intermediate dict.
        """
        # Run validation to get a real report
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Convert report to dict
        report_dict = report_to_dict(report)

        # Serialize to JSON
        json_str = json.dumps(report_dict)

        # Parse JSON back to dict
        parsed_dict = json.loads(json_str)

        # Verify key fields match
        assert parsed_dict["timestamp"] == report_dict["timestamp"]
        assert parsed_dict["ifc_file"] == report_dict["ifc_file"]
        assert parsed_dict["total_specifications"] == report_dict["total_specifications"]
        assert parsed_dict["passed_specifications"] == report_dict["passed_specifications"]
        assert parsed_dict["pass_rate_percent"] == report_dict["pass_rate_percent"]
        assert parsed_dict["success"] == report_dict["success"]

        # Verify nested structures roundtrip correctly
        assert len(parsed_dict["specifications"]) == len(report_dict["specifications"])
        for i, spec in enumerate(parsed_dict["specifications"]):
            orig_spec = report_dict["specifications"][i]
            assert spec["name"] == orig_spec["name"]
            assert spec["passed"] == orig_spec["passed"]
            assert len(spec["failures"]) == len(orig_spec["failures"])

    def test_report_to_dict_with_failures(
        self, ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that report with failures serializes correctly.

        This specifically tests that EntityFailure objects with various
        attribute values (including None) are properly serialized.
        """
        # Run validation - we know NL_BIM_Basis_ILS_v2.ids has failures
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Convert to dict
        report_dict = report_to_dict(report)

        # Find specifications with failures
        specs_with_failures = [
            spec for spec in report_dict["specifications"]
            if len(spec["failures"]) > 0
        ]

        # Verify we have failures to test
        assert len(specs_with_failures) > 0, (
            "Expected at least one specification with failures to test serialization"
        )

        # Verify failure dict structure for each failure
        for spec in specs_with_failures:
            for failure in spec["failures"]:
                # Verify entity_id is an integer
                assert isinstance(failure["entity_id"], int), (
                    f"entity_id should be int after serialization, "
                    f"got {type(failure['entity_id']).__name__}"
                )

                # Verify entity_type is a string
                assert isinstance(failure["entity_type"], str), (
                    f"entity_type should be str after serialization, "
                    f"got {type(failure['entity_type']).__name__}"
                )

                # Verify optional fields are str or None
                assert failure["entity_name"] is None or isinstance(failure["entity_name"], str), (
                    "entity_name should be str or None after serialization"
                )
                assert failure["global_id"] is None or isinstance(failure["global_id"], str), (
                    "global_id should be str or None after serialization"
                )

    def test_report_to_dict_json_pretty_print(
        self, ifc_path: Path, ids_path: Path
    ) -> None:
        """Test that report can be serialized to formatted JSON.

        This tests that json.dumps() with formatting options (indent) works
        correctly, which is important for human-readable output.
        """
        # Run validation
        report = validate_ifc_against_ids(ifc_path, ids_path)

        # Convert to dict
        report_dict = report_to_dict(report)

        # Serialize with pretty printing
        try:
            json_str = json.dumps(report_dict, indent=2)
        except (TypeError, ValueError) as e:
            pytest.fail(f"json.dumps() with indent failed: {e}")

        # Verify the formatted output contains expected structure
        assert "timestamp" in json_str
        assert "specifications" in json_str
        assert "\n" in json_str  # Should have newlines from indent

        # Verify it's still valid JSON
        parsed = json.loads(json_str)
        assert parsed["total_specifications"] == report.total_specifications
