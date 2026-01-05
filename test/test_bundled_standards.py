"""Unit tests for bundled Dutch BIM standards functionality.

Tests cover:
- Bundled IDS files accessibility via importlib.resources
- Shortcut resolution (nl-bim, rvb) to correct file paths
- Invalid shortcut error handling with helpful messages
- IDS files validity (parseable by ifctester)
- Integration tests for CLI validation with bundled standards
- Backward compatibility with file path --ids parameter

Usage:
    pytest test/test_bundled_standards.py -v
    pytest test/test_bundled_standards.py --cov=src --cov-report=term-missing
"""

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ifc_validator.cli import app
from ifc_validator.standards import (
    STANDARD_SHORTCUTS,
    get_bundled_ids,
    get_standard_filename,
    is_shortcut,
    list_available_standards,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a CliRunner instance for CLI testing."""
    return CliRunner()


@pytest.fixture
def sample_ifc_path() -> Path:
    """Path to sample IFC file for validation tests.

    Returns the path to the sample.ifc file in test/fixtures/.
    This is a minimal IFC file suitable for basic validation tests.
    """
    return Path(__file__).parent / "fixtures" / "sample.ifc"


@pytest.fixture
def sample_ids_path() -> Path:
    """Path to sample IDS file for backward compatibility tests.

    Returns the path to the sample.ids file in test/fixtures/.
    """
    return Path(__file__).parent / "fixtures" / "sample.ids"


@pytest.fixture
def large_ifc_path() -> Path:
    """Path to larger IFC file for comprehensive validation tests.

    Returns the path to the 2786_CLT_model.ifc file in the test directory.
    This is an IFC4X3 model with ~154K entities.
    """
    return Path(__file__).parent / "2786_CLT_model.ifc"


@pytest.fixture
def all_shortcuts() -> list[str]:
    """List of all valid standard shortcuts.

    Returns all shortcuts that should be recognized by the resolver.
    """
    return ['nl-bim', 'rvb']


@pytest.fixture
def nl_bim_filename() -> str:
    """Expected filename for nl-bim shortcut."""
    return 'NL_BIM_Basis_ILS_v2.ids'


@pytest.fixture
def rvb_filename() -> str:
    """Expected filename for rvb shortcut."""
    return 'RVB_BIM_Norm_v1.1.ids'


# =============================================================================
# Fixture Verification Tests
# =============================================================================


class TestFixtures:
    """Verify test fixtures are set up correctly."""

    def test_sample_ifc_path_exists(self, sample_ifc_path: Path) -> None:
        """Verify the sample IFC file exists."""
        assert sample_ifc_path.exists(), f"Sample IFC file not found: {sample_ifc_path}"
        assert sample_ifc_path.suffix.lower() == ".ifc"

    def test_sample_ids_path_exists(self, sample_ids_path: Path) -> None:
        """Verify the sample IDS file exists."""
        assert sample_ids_path.exists(), f"Sample IDS file not found: {sample_ids_path}"
        assert sample_ids_path.suffix.lower() == ".ids"

    def test_large_ifc_path_exists(self, large_ifc_path: Path) -> None:
        """Verify the large test IFC file exists."""
        assert large_ifc_path.exists(), f"Large IFC file not found: {large_ifc_path}"
        assert large_ifc_path.suffix.lower() == ".ifc"

    def test_all_shortcuts_fixture(self, all_shortcuts: list[str]) -> None:
        """Verify all_shortcuts fixture contains expected shortcuts."""
        assert 'nl-bim' in all_shortcuts
        assert 'rvb' in all_shortcuts
        assert len(all_shortcuts) == 2

    def test_standard_shortcuts_constant_available(self) -> None:
        """Verify STANDARD_SHORTCUTS constant is importable and populated."""
        assert STANDARD_SHORTCUTS is not None
        assert isinstance(STANDARD_SHORTCUTS, dict)
        assert len(STANDARD_SHORTCUTS) >= 2


# =============================================================================
# Bundled Standards Existence Tests (3.2)
# =============================================================================


class TestBundledStandardsExist:
    """Test that bundled IDS files are accessible via importlib.resources.

    QA Criteria: test_bundled_standards_exist
    - Verify NL_BIM and RVB IDS files accessible via importlib.resources
    """

    def test_standards_package_importable(self) -> None:
        """Verify ifc_validator.standards package is importable.

        This test ensures the standards subpackage is correctly set up
        and can be imported via importlib.resources.
        """
        from importlib.resources import files

        standards_dir = files('ifc_validator.standards')
        assert standards_dir is not None, "Standards package should be accessible"

    def test_nl_bim_ids_accessible_via_importlib(self, nl_bim_filename: str) -> None:
        """Verify NL_BIM IDS file is accessible via importlib.resources.

        This test verifies:
        - NL_BIM_Basis_ILS_v2.ids exists in the standards package
        - The file can be located using importlib.resources.files()
        - The resolved path actually exists on the filesystem
        """
        from importlib.resources import files

        standards_dir = files('ifc_validator.standards')
        resource = standards_dir / nl_bim_filename

        # Verify the resource can be resolved to a path
        resource_path = Path(str(resource))
        assert resource_path.exists(), (
            f"NL_BIM IDS file should exist at {resource_path}"
        )
        assert resource_path.suffix.lower() == '.ids', (
            f"File should have .ids extension, got {resource_path.suffix}"
        )

    def test_rvb_ids_accessible_via_importlib(self, rvb_filename: str) -> None:
        """Verify RVB IDS file is accessible via importlib.resources.

        This test verifies:
        - RVB_BIM_Norm_v1.1.ids exists in the standards package
        - The file can be located using importlib.resources.files()
        - The resolved path actually exists on the filesystem
        """
        from importlib.resources import files

        standards_dir = files('ifc_validator.standards')
        resource = standards_dir / rvb_filename

        # Verify the resource can be resolved to a path
        resource_path = Path(str(resource))
        assert resource_path.exists(), (
            f"RVB IDS file should exist at {resource_path}"
        )
        assert resource_path.suffix.lower() == '.ids', (
            f"File should have .ids extension, got {resource_path.suffix}"
        )

    def test_nl_bim_ids_file_not_empty(self, nl_bim_filename: str) -> None:
        """Verify NL_BIM IDS file has content and is valid XML.

        This ensures the bundled file is not corrupted or empty.
        """
        from importlib.resources import files

        standards_dir = files('ifc_validator.standards')
        resource_path = Path(str(standards_dir / nl_bim_filename))

        # File should have content
        file_size = resource_path.stat().st_size
        assert file_size > 0, "NL_BIM IDS file should not be empty"

        # File should start with XML declaration or IDS element
        content = resource_path.read_text(encoding='utf-8')[:100]
        assert '<?xml' in content or '<ids' in content.lower(), (
            "NL_BIM IDS file should contain valid XML/IDS content"
        )

    def test_rvb_ids_file_not_empty(self, rvb_filename: str) -> None:
        """Verify RVB IDS file has content and is valid XML.

        This ensures the bundled file is not corrupted or empty.
        """
        from importlib.resources import files

        standards_dir = files('ifc_validator.standards')
        resource_path = Path(str(standards_dir / rvb_filename))

        # File should have content
        file_size = resource_path.stat().st_size
        assert file_size > 0, "RVB IDS file should not be empty"

        # File should start with XML declaration or IDS element
        content = resource_path.read_text(encoding='utf-8')[:100]
        assert '<?xml' in content or '<ids' in content.lower(), (
            "RVB IDS file should contain valid XML/IDS content"
        )

    def test_get_bundled_ids_returns_valid_path_for_nl_bim(self) -> None:
        """Verify get_bundled_ids() returns a valid Path for nl-bim shortcut.

        This test verifies the resolver function correctly resolves the
        nl-bim shortcut to a valid, existing file path.
        """
        path = get_bundled_ids('nl-bim')

        assert isinstance(path, Path), f"Expected Path, got {type(path).__name__}"
        assert path.exists(), f"Resolved path should exist: {path}"
        assert path.name == 'NL_BIM_Basis_ILS_v2.ids', (
            f"Expected NL_BIM_Basis_ILS_v2.ids, got {path.name}"
        )

    def test_get_bundled_ids_returns_valid_path_for_rvb(self) -> None:
        """Verify get_bundled_ids() returns a valid Path for rvb shortcut.

        This test verifies the resolver function correctly resolves the
        rvb shortcut to a valid, existing file path.
        """
        path = get_bundled_ids('rvb')

        assert isinstance(path, Path), f"Expected Path, got {type(path).__name__}"
        assert path.exists(), f"Resolved path should exist: {path}"
        assert path.name == 'RVB_BIM_Norm_v1.1.ids', (
            f"Expected RVB_BIM_Norm_v1.1.ids, got {path.name}"
        )

    def test_all_shortcuts_resolve_to_existing_files(self, all_shortcuts: list[str]) -> None:
        """Verify all defined shortcuts resolve to existing IDS files.

        This is a parameterized-style test that ensures every shortcut
        in the system can be resolved to a valid file.
        """
        for shortcut in all_shortcuts:
            path = get_bundled_ids(shortcut)
            assert path.exists(), (
                f"Shortcut '{shortcut}' should resolve to existing file, "
                f"but {path} does not exist"
            )
            assert path.suffix.lower() == '.ids', (
                f"Shortcut '{shortcut}' should resolve to .ids file, "
                f"got {path.suffix}"
            )

    def test_standard_shortcuts_matches_available_standards(self) -> None:
        """Verify STANDARD_SHORTCUTS constant matches list_available_standards().

        This ensures consistency between the constant and the function.
        """
        available = list_available_standards()
        shortcut_keys = list(STANDARD_SHORTCUTS.keys())

        assert set(available) == set(shortcut_keys), (
            f"list_available_standards() should return same shortcuts as "
            f"STANDARD_SHORTCUTS.keys(). Got {available} vs {shortcut_keys}"
        )


# =============================================================================
# Shortcut Resolution Tests (3.3)
# =============================================================================


class TestShortcutResolution:
    """Test that shortcuts resolve to correct file paths.

    QA Criteria: test_shortcut_resolution
    - Verify nl-bim and rvb shortcuts resolve to correct file paths
    """

    # -------------------------------------------------------------------------
    # Basic Resolution Tests
    # -------------------------------------------------------------------------

    def test_nl_bim_shortcut_resolves_to_path(self) -> None:
        """Verify nl-bim shortcut resolves to a Path object.

        This test verifies:
        - get_bundled_ids('nl-bim') returns a Path instance
        - The returned path is not None
        """
        result = get_bundled_ids('nl-bim')

        assert result is not None, "nl-bim should resolve to a path"
        assert isinstance(result, Path), (
            f"Expected Path, got {type(result).__name__}"
        )

    def test_rvb_shortcut_resolves_to_path(self) -> None:
        """Verify rvb shortcut resolves to a Path object.

        This test verifies:
        - get_bundled_ids('rvb') returns a Path instance
        - The returned path is not None
        """
        result = get_bundled_ids('rvb')

        assert result is not None, "rvb should resolve to a path"
        assert isinstance(result, Path), (
            f"Expected Path, got {type(result).__name__}"
        )

    # -------------------------------------------------------------------------
    # Correct Filename Tests
    # -------------------------------------------------------------------------

    def test_nl_bim_resolves_to_correct_filename(
        self, nl_bim_filename: str
    ) -> None:
        """Verify nl-bim shortcut resolves to the correct IDS filename.

        This test verifies:
        - The resolved path ends with 'NL_BIM_Basis_ILS_v2.ids'
        - The filename matches exactly (case-sensitive)
        """
        result = get_bundled_ids('nl-bim')

        assert result.name == nl_bim_filename, (
            f"nl-bim should resolve to '{nl_bim_filename}', "
            f"got '{result.name}'"
        )

    def test_rvb_resolves_to_correct_filename(
        self, rvb_filename: str
    ) -> None:
        """Verify rvb shortcut resolves to the correct IDS filename.

        This test verifies:
        - The resolved path ends with 'RVB_BIM_Norm_v1.1.ids'
        - The filename matches exactly (case-sensitive)
        """
        result = get_bundled_ids('rvb')

        assert result.name == rvb_filename, (
            f"rvb should resolve to '{rvb_filename}', "
            f"got '{result.name}'"
        )

    # -------------------------------------------------------------------------
    # Resolved Paths Exist and Are Valid
    # -------------------------------------------------------------------------

    def test_nl_bim_resolved_path_exists(self) -> None:
        """Verify nl-bim resolved path points to an existing file."""
        result = get_bundled_ids('nl-bim')

        assert result.exists(), (
            f"nl-bim resolved path should exist on filesystem: {result}"
        )
        assert result.is_file(), (
            f"nl-bim resolved path should be a file, not directory: {result}"
        )

    def test_rvb_resolved_path_exists(self) -> None:
        """Verify rvb resolved path points to an existing file."""
        result = get_bundled_ids('rvb')

        assert result.exists(), (
            f"rvb resolved path should exist on filesystem: {result}"
        )
        assert result.is_file(), (
            f"rvb resolved path should be a file, not directory: {result}"
        )

    def test_nl_bim_resolved_path_has_ids_extension(self) -> None:
        """Verify nl-bim resolved path has .ids extension."""
        result = get_bundled_ids('nl-bim')

        assert result.suffix.lower() == '.ids', (
            f"nl-bim should resolve to .ids file, got '{result.suffix}'"
        )

    def test_rvb_resolved_path_has_ids_extension(self) -> None:
        """Verify rvb resolved path has .ids extension."""
        result = get_bundled_ids('rvb')

        assert result.suffix.lower() == '.ids', (
            f"rvb should resolve to .ids file, got '{result.suffix}'"
        )

    # -------------------------------------------------------------------------
    # is_shortcut() Function Tests
    # -------------------------------------------------------------------------

    def test_is_shortcut_returns_true_for_nl_bim(self) -> None:
        """Verify is_shortcut() returns True for 'nl-bim'."""
        assert is_shortcut('nl-bim') is True, (
            "is_shortcut('nl-bim') should return True"
        )

    def test_is_shortcut_returns_true_for_rvb(self) -> None:
        """Verify is_shortcut() returns True for 'rvb'."""
        assert is_shortcut('rvb') is True, (
            "is_shortcut('rvb') should return True"
        )

    def test_is_shortcut_returns_false_for_file_path(self) -> None:
        """Verify is_shortcut() returns False for file paths."""
        test_paths = [
            '/path/to/file.ids',
            'file.ids',
            '../other/file.ids',
            'C:\\path\\to\\file.ids',
        ]
        for path in test_paths:
            assert is_shortcut(path) is False, (
                f"is_shortcut('{path}') should return False"
            )

    def test_is_shortcut_returns_false_for_invalid_shortcuts(self) -> None:
        """Verify is_shortcut() returns False for unrecognized shortcuts."""
        invalid_values = [
            'unknown',
            'NL-BIM',  # Wrong case
            'RVB',  # Wrong case
            'nl_bim',  # Underscore instead of hyphen
            'nlbim',  # No separator
            '',  # Empty string
        ]
        for value in invalid_values:
            assert is_shortcut(value) is False, (
                f"is_shortcut('{value}') should return False"
            )

    # -------------------------------------------------------------------------
    # get_standard_filename() Function Tests
    # -------------------------------------------------------------------------

    def test_get_standard_filename_for_nl_bim(
        self, nl_bim_filename: str
    ) -> None:
        """Verify get_standard_filename() returns correct name for nl-bim."""
        result = get_standard_filename('nl-bim')

        assert result == nl_bim_filename, (
            f"Expected '{nl_bim_filename}', got '{result}'"
        )

    def test_get_standard_filename_for_rvb(
        self, rvb_filename: str
    ) -> None:
        """Verify get_standard_filename() returns correct name for rvb."""
        result = get_standard_filename('rvb')

        assert result == rvb_filename, (
            f"Expected '{rvb_filename}', got '{result}'"
        )

    # -------------------------------------------------------------------------
    # Case Sensitivity Tests
    # -------------------------------------------------------------------------

    def test_shortcuts_are_case_sensitive(self) -> None:
        """Verify shortcuts are case-sensitive (lowercase only).

        This test ensures that uppercase or mixed-case variants of shortcuts
        are not recognized. Only lowercase shortcuts are valid.
        """
        invalid_case_variants = [
            'NL-BIM',
            'Nl-Bim',
            'nl-BIM',
            'RVB',
            'Rvb',
        ]
        for variant in invalid_case_variants:
            assert is_shortcut(variant) is False, (
                f"is_shortcut('{variant}') should return False (case-sensitive)"
            )

    # -------------------------------------------------------------------------
    # Resolved Paths Location Tests
    # -------------------------------------------------------------------------

    def test_nl_bim_resolved_in_standards_directory(self) -> None:
        """Verify nl-bim resolves to a file in the standards package directory.

        The resolved path should be inside the ifc_validator/standards/ directory.
        """
        result = get_bundled_ids('nl-bim')

        # Parent directory should be named 'standards'
        assert result.parent.name == 'standards', (
            f"nl-bim should resolve to standards directory, "
            f"got parent '{result.parent.name}'"
        )

    def test_rvb_resolved_in_standards_directory(self) -> None:
        """Verify rvb resolves to a file in the standards package directory.

        The resolved path should be inside the ifc_validator/standards/ directory.
        """
        result = get_bundled_ids('rvb')

        # Parent directory should be named 'standards'
        assert result.parent.name == 'standards', (
            f"rvb should resolve to standards directory, "
            f"got parent '{result.parent.name}'"
        )

    # -------------------------------------------------------------------------
    # list_available_standards() Tests
    # -------------------------------------------------------------------------

    def test_list_available_standards_contains_both_shortcuts(self) -> None:
        """Verify list_available_standards() returns both shortcuts."""
        available = list_available_standards()

        assert 'nl-bim' in available, "nl-bim should be in available standards"
        assert 'rvb' in available, "rvb should be in available standards"

    def test_list_available_standards_returns_list(self) -> None:
        """Verify list_available_standards() returns a list."""
        available = list_available_standards()

        assert isinstance(available, list), (
            f"Expected list, got {type(available).__name__}"
        )

    def test_all_listed_standards_can_be_resolved(self) -> None:
        """Verify every shortcut from list_available_standards() can be resolved.

        This is a comprehensive test that ensures consistency between
        the listing and resolution functions.
        """
        for shortcut in list_available_standards():
            # Should not raise
            path = get_bundled_ids(shortcut)
            assert path.exists(), (
                f"Shortcut '{shortcut}' from list_available_standards() "
                f"should resolve to an existing file"
            )

    # -------------------------------------------------------------------------
    # STANDARD_SHORTCUTS Constant Tests
    # -------------------------------------------------------------------------

    def test_standard_shortcuts_contains_nl_bim(
        self, nl_bim_filename: str
    ) -> None:
        """Verify STANDARD_SHORTCUTS constant contains nl-bim mapping."""
        assert 'nl-bim' in STANDARD_SHORTCUTS, (
            "STANDARD_SHORTCUTS should contain 'nl-bim' key"
        )
        assert STANDARD_SHORTCUTS['nl-bim'] == nl_bim_filename, (
            f"STANDARD_SHORTCUTS['nl-bim'] should be '{nl_bim_filename}'"
        )

    def test_standard_shortcuts_contains_rvb(
        self, rvb_filename: str
    ) -> None:
        """Verify STANDARD_SHORTCUTS constant contains rvb mapping."""
        assert 'rvb' in STANDARD_SHORTCUTS, (
            "STANDARD_SHORTCUTS should contain 'rvb' key"
        )
        assert STANDARD_SHORTCUTS['rvb'] == rvb_filename, (
            f"STANDARD_SHORTCUTS['rvb'] should be '{rvb_filename}'"
        )


# =============================================================================
# Invalid Shortcut Error Handling Tests (3.4)
# =============================================================================


class TestInvalidShortcutError:
    """Test graceful error handling for unknown shortcuts.

    QA Criteria: test_invalid_shortcut
    - Verify graceful error for unknown shortcuts with helpful message
    """

    pass  # Tests to be added in subtask 3.4


# =============================================================================
# IDS Files Validity Tests (3.5)
# =============================================================================


class TestIDSFilesValidity:
    """Test that bundled IDS files can be opened and parsed by ifctester.

    Acceptance Criteria:
    - Test verifies both IDS files load successfully with ifctester.ids.open()
    """

    pass  # Tests to be added in subtask 3.5


# =============================================================================
# Integration Tests - Validation with nl-bim (4.1)
# =============================================================================


class TestValidationWithNlBim:
    """End-to-end test validating IFC file with --ids nl-bim shortcut.

    QA Criteria: test_validation_with_nl_bim
    - End-to-end validation with --ids nl-bim produces valid results
    """

    pass  # Tests to be added in subtask 4.1


# =============================================================================
# Integration Tests - Validation with rvb (4.2)
# =============================================================================


class TestValidationWithRvb:
    """End-to-end test validating IFC file with --ids rvb shortcut.

    QA Criteria: test_validation_with_rvb
    - End-to-end validation with --ids rvb produces valid results
    """

    pass  # Tests to be added in subtask 4.2


# =============================================================================
# Integration Tests - Backward Compatibility (4.3)
# =============================================================================


class TestBackwardCompatibility:
    """Test that existing --ids /path/to/file.ids usage still works.

    QA Criteria: test_backward_compatibility
    - Existing --ids /path/to/file.ids usage still works
    """

    pass  # Tests to be added in subtask 4.3
