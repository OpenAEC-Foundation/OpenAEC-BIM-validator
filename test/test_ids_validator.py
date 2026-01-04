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
