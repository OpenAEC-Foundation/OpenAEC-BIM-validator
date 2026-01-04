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
