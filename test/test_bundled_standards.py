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

    pass  # Tests to be added in subtask 3.2


# =============================================================================
# Shortcut Resolution Tests (3.3)
# =============================================================================


class TestShortcutResolution:
    """Test that shortcuts resolve to correct file paths.

    QA Criteria: test_shortcut_resolution
    - Verify nl-bim and rvb shortcuts resolve to correct file paths
    """

    pass  # Tests to be added in subtask 3.3


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
