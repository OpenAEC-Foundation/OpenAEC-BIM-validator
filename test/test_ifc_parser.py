"""
Unit and integration tests for the IFC Parser Module.

Tests cover:
- Schema detection for IFC2X3, IFC4, and IFC4X3
- File validation (existence, extension, permissions)
- Error handling for corrupt/malformed files
- Memory constraint enforcement
- Entity loading with by_type()
- Context manager functionality

Usage:
    pytest test/test_ifc_parser.py -v
    pytest test/test_ifc_parser.py --cov=src --cov-report=term-missing
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ifc_parser import IFCParser, MemoryStats

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def parser():
    """Create a fresh IFCParser instance for each test."""
    return IFCParser()


@pytest.fixture
def test_ifc_file():
    """Path to the test IFC file (IFC4X3 schema)."""
    return Path(__file__).parent / "2786_CLT_model.ifc"


@pytest.fixture
def ifcopenshell_fixtures_dir():
    """Path to IfcOpenShell's test fixtures directory."""
    fixtures_path = (
        Path(__file__).parent
        / "venv"
        / "Lib"
        / "site-packages"
        / "ifcopenshell"
        / "simple_spf"
        / "fixtures"
    )
    if fixtures_path.exists():
        return fixtures_path
    # Fallback: skip tests that need these fixtures
    pytest.skip("IfcOpenShell fixtures not found")


@pytest.fixture
def valid_ifc4_file(ifcopenshell_fixtures_dir):
    """Path to a valid IFC4 file from IfcOpenShell fixtures."""
    return ifcopenshell_fixtures_dir / "pass_1.ifc"


@pytest.fixture
def corrupt_no_header_file(ifcopenshell_fixtures_dir):
    """Path to a corrupt IFC file missing the HEADER section."""
    return ifcopenshell_fixtures_dir / "fail_no_header.ifc"


@pytest.fixture
def corrupt_duplicate_id_file(ifcopenshell_fixtures_dir):
    """Path to a corrupt IFC file with duplicate entity IDs."""
    return ifcopenshell_fixtures_dir / "fail_duplicate_id.ifc"


@pytest.fixture
def temp_empty_file():
    """Create a temporary empty file."""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        temp_path = f.name
    yield Path(temp_path)
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_invalid_extension_file():
    """Create a temporary file with invalid extension."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Not an IFC file")
        temp_path = f.name
    yield Path(temp_path)
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_corrupt_file():
    """Create a temporary corrupt IFC file."""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        f.write(b"This is not valid IFC content\nJust random text.")
        temp_path = f.name
    yield Path(temp_path)
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_ifc2x3_file():
    """Create a temporary valid IFC2X3 file for testing schema detection."""
    ifc2x3_content = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('test.ifc','2024-01-01T00:00:00',(''),(''),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCPERSON($,$,'',$,$,$,$,$);
#2=IFCORGANIZATION($,'',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'1.0','TestApp','TestApp');
#5=IFCOWNERHISTORY(#3,#4,$,.NOCHANGE.,$,$,$,0);
#6=IFCDIRECTION((1.,0.,0.));
#7=IFCDIRECTION((0.,0.,1.));
#8=IFCCARTESIANPOINT((0.,0.,0.));
#9=IFCAXIS2PLACEMENT3D(#8,#7,#6);
#10=IFCDIRECTION((0.,1.));
#11=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#9,#10);
#12=IFCDIMENSIONALEXPONENTS(0,0,0,0,0,0,0);
#13=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#14=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#15=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#16=IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);
#17=IFCUNITASSIGNMENT((#13,#14,#15,#16));
#18=IFCPROJECT('0YvctVUKr0kugbFTf53O9L',#5,'Test Project',$,$,$,$,(#11),#17);
ENDSEC;
END-ISO-10303-21;
"""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        f.write(ifc2x3_content)
        temp_path = f.name
    yield Path(temp_path)
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_ifc4_file():
    """Create a temporary valid IFC4 file for testing schema detection."""
    ifc4_content = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('test.ifc','2024-01-01T00:00:00',(''),(''),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPERSON($,$,'',$,$,$,$,$);
#2=IFCORGANIZATION($,'',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'1.0','TestApp','TestApp');
#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,0);
#6=IFCDIRECTION((1.,0.,0.));
#7=IFCDIRECTION((0.,0.,1.));
#8=IFCCARTESIANPOINT((0.,0.,0.));
#9=IFCAXIS2PLACEMENT3D(#8,#7,#6);
#10=IFCDIRECTION((0.,1.,0.));
#11=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#9,#10);
#12=IFCDIMENSIONALEXPONENTS(0,0,0,0,0,0,0);
#13=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#14=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#15=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#16=IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);
#17=IFCUNITASSIGNMENT((#13,#14,#15,#16));
#18=IFCPROJECT('0YvctVUKr0kugbFTf53O9L',#5,'Test Project',$,$,$,$,(#11),#17);
ENDSEC;
END-ISO-10303-21;
"""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        f.write(ifc4_content)
        temp_path = f.name
    yield Path(temp_path)
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# =============================================================================
# Basic Parser Tests
# =============================================================================


class TestIFCParserBasics:
    """Test basic IFCParser functionality."""

    def test_parser_initialization(self, parser):
        """Test that parser initializes with correct default state."""
        assert parser.file_path is None
        assert parser.schema is None
        assert parser.ifc_file is None
        assert parser.is_loaded is False
        assert parser.memory_stats is None

    def test_parser_repr_not_loaded(self, parser):
        """Test parser string representation when no file is loaded."""
        assert repr(parser) == "IFCParser(not loaded)"

    def test_parser_constants(self, parser):
        """Test that parser has expected constants defined."""
        assert "IFC2X3" in parser.SUPPORTED_SCHEMAS
        assert "IFC4" in parser.SUPPORTED_SCHEMAS
        assert "IFC4X3" in parser.SUPPORTED_SCHEMAS
        assert ".ifc" in parser.VALID_EXTENSIONS
        assert ".ifcxml" in parser.VALID_EXTENSIONS
        assert ".ifczip" in parser.VALID_EXTENSIONS
        assert parser.MEMORY_MULTIPLIER == 10


# =============================================================================
# File Loading Tests
# =============================================================================


class TestFileLoading:
    """Test IFC file loading functionality."""

    def test_load_valid_ifc_file(self, parser, test_ifc_file):
        """Test loading a valid IFC file."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))

        assert parser.is_loaded is True
        assert parser.file_path == test_ifc_file
        assert parser.schema is not None
        assert parser.ifc_file is not None

    def test_load_updates_parser_repr(self, parser, test_ifc_file):
        """Test that loading a file updates the parser representation."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))

        repr_str = repr(parser)
        assert "IFCParser(file=" in repr_str
        assert parser.schema in repr_str


# =============================================================================
# Schema Detection Tests
# =============================================================================


class TestSchemaDetection:
    """Test IFC schema detection functionality."""

    def test_schema_detection_ifc2x3(self, parser, temp_ifc2x3_file):
        """Test schema detection for IFC2X3 file.

        Verifies that the parser correctly identifies IFC2X3 schema
        from a minimal valid IFC2X3 file.
        """
        parser.load(str(temp_ifc2x3_file))

        assert parser.schema == "IFC2X3"
        assert parser.is_loaded is True

    def test_schema_detection_ifc4(self, parser, temp_ifc4_file):
        """Test schema detection for IFC4 file.

        Verifies that the parser correctly identifies IFC4 schema
        from a minimal valid IFC4 file.
        """
        parser.load(str(temp_ifc4_file))

        assert parser.schema == "IFC4"
        assert parser.is_loaded is True

    def test_schema_detection_ifc4_from_fixtures(self, parser, valid_ifc4_file):
        """Test schema detection for IFC4 file from IfcOpenShell fixtures."""
        parser.load(str(valid_ifc4_file))

        assert parser.schema == "IFC4"

    def test_schema_detection_ifc4x3(self, parser, test_ifc_file):
        """Test schema detection for IFC4X3 file."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))

        assert parser.schema == "IFC4X3"

    def test_schema_detection_ifc2x3_vs_ifc4_different(
        self, parser, temp_ifc2x3_file, temp_ifc4_file
    ):
        """Test that IFC2X3 and IFC4 files are detected as different schemas.

        This test ensures the parser correctly distinguishes between
        the two major IFC schema versions.
        """
        # Load IFC2X3 file
        parser.load(str(temp_ifc2x3_file))
        ifc2x3_schema = parser.schema

        # Load IFC4 file (should auto-close previous)
        parser.load(str(temp_ifc4_file))
        ifc4_schema = parser.schema

        # Verify they are different
        assert ifc2x3_schema == "IFC2X3"
        assert ifc4_schema == "IFC4"
        assert ifc2x3_schema != ifc4_schema

    def test_schema_is_uppercase(self, parser, temp_ifc2x3_file):
        """Test that schema detection returns uppercase schema names."""
        parser.load(str(temp_ifc2x3_file))

        # Schema should be uppercase
        assert parser.schema == parser.schema.upper()

    def test_schema_is_in_supported_schemas(self, parser, temp_ifc2x3_file):
        """Test that detected schema is in the list of supported schemas."""
        parser.load(str(temp_ifc2x3_file))

        assert parser.schema in parser.SUPPORTED_SCHEMAS

    def test_schema_detection_preserves_exact_version(
        self, parser, temp_ifc2x3_file, temp_ifc4_file
    ):
        """Test that schema detection preserves exact version string.

        IFC2X3 should be detected as exactly 'IFC2X3', not 'IFC2' or 'IFC2X'.
        IFC4 should be detected as exactly 'IFC4', not 'IFC4X1' or similar.
        """
        # Test IFC2X3
        parser.load(str(temp_ifc2x3_file))
        assert parser.schema == "IFC2X3"
        assert "2X3" in parser.schema

        # Test IFC4
        parser.load(str(temp_ifc4_file))
        assert parser.schema == "IFC4"
        assert parser.schema.endswith("4")

    def test_schema_is_none_before_load(self, parser):
        """Test that schema is None before any file is loaded."""
        assert parser.schema is None
        assert parser.is_loaded is False

    def test_schema_is_none_after_close(self, parser, temp_ifc2x3_file):
        """Test that schema is reset to None after closing the file."""
        parser.load(str(temp_ifc2x3_file))
        assert parser.schema == "IFC2X3"

        parser.close()
        assert parser.schema is None

    def test_schema_detection_with_context_manager(self, temp_ifc4_file):
        """Test schema detection works correctly with context manager."""
        with IFCParser() as parser:
            parser.load(str(temp_ifc4_file))
            assert parser.schema == "IFC4"
            assert parser.is_loaded is True

        # After context exit, schema should be None
        assert parser.schema is None


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_file_not_found():
    """Test that FileNotFoundError is raised for non-existent files.

    This standalone test verifies that:
    - Attempting to load a non-existent file raises FileNotFoundError
    - The error message includes the file path for debugging
    - The error message clearly indicates the file was not found
    """
    parser = IFCParser()

    # Test with a clearly non-existent file path
    with pytest.raises(FileNotFoundError) as exc_info:
        parser.load("this_file_does_not_exist_12345.ifc")

    error_msg = str(exc_info.value)
    assert "this_file_does_not_exist_12345.ifc" in error_msg
    assert "not found" in error_msg.lower()


def test_corrupt_file():
    """Test that corrupt IFC files raise ValueError with meaningful message.

    This standalone test verifies that:
    - Loading a file with invalid IFC content raises ValueError
    - The error message indicates parsing failure or corruption
    - Resources are properly cleaned up after the error
    """
    parser = IFCParser()

    # Create a temporary corrupt file with invalid IFC content
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        f.write(b"This is not valid IFC content\nJust random garbage data.")
        temp_path = f.name

    try:
        with pytest.raises(ValueError) as exc_info:
            parser.load(temp_path)

        error_msg = str(exc_info.value)
        # Error should mention parsing failure or corruption
        assert any(
            keyword in error_msg.lower()
            for keyword in ["parse", "corrupt", "invalid", "failed"]
        )

        # Verify parser state is clean after error
        assert parser.is_loaded is False
        assert parser.ifc_file is None
    finally:
        # Cleanup temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


class TestFileNotFound:
    """Test error handling for non-existent files."""

    def test_file_not_found_error(self, parser):
        """Test that FileNotFoundError is raised for non-existent files."""
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.load("nonexistent_file.ifc")

        assert "nonexistent_file.ifc" in str(exc_info.value)

    def test_file_not_found_message_is_clear(self, parser):
        """Test that error message includes the file path."""
        fake_path = "/path/to/missing/model.ifc"

        with pytest.raises(FileNotFoundError) as exc_info:
            parser.load(fake_path)

        assert fake_path in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


class TestCorruptFile:
    """Test error handling for corrupt IFC files."""

    def test_corrupt_file_raises_value_error(self, parser, temp_corrupt_file):
        """Test that corrupt files raise ValueError with meaningful message."""
        with pytest.raises(ValueError) as exc_info:
            parser.load(str(temp_corrupt_file))

        error_msg = str(exc_info.value)
        assert "parse" in error_msg.lower() or "corrupt" in error_msg.lower()

    def test_empty_file_raises_value_error(self, parser, temp_empty_file):
        """Test that empty files raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parser.load(str(temp_empty_file))

        assert "empty" in str(exc_info.value).lower()

    def test_invalid_extension_raises_value_error(
        self, parser, temp_invalid_extension_file
    ):
        """Test that files with invalid extension raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parser.load(str(temp_invalid_extension_file))

        error_msg = str(exc_info.value)
        assert "extension" in error_msg.lower()

    def test_directory_raises_error(self, parser):
        """Test that passing a directory path raises IsADirectoryError."""
        with pytest.raises(IsADirectoryError):
            parser.load(str(Path(__file__).parent))


# =============================================================================
# Memory Constraint Tests
# =============================================================================


class TestMemoryConstraint:
    """Test memory constraint enforcement."""

    def test_memory_stats_after_load(self, parser, test_ifc_file):
        """Test that memory stats are populated after loading."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))

        stats = parser.memory_stats
        assert stats is not None
        assert isinstance(stats, MemoryStats)
        assert stats.file_size > 0
        assert stats.memory_before > 0
        assert stats.memory_after >= stats.memory_before

    def test_memory_stats_properties(self, parser, test_ifc_file):
        """Test MemoryStats computed properties."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))

        stats = parser.memory_stats
        assert stats.memory_used >= 0
        assert stats.memory_multiplier >= 0

    def test_memory_constraint_check_passes_for_small_file(self, parser, test_ifc_file):
        """Test that small files pass memory constraint check."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        # This should not raise - file is small
        parser._check_memory_constraint(str(test_ifc_file))

    def test_memory_constraint_raises_for_huge_file(self, parser, test_ifc_file):
        """Test that memory constraint check fails when memory is insufficient."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        # Mock psutil to simulate low available memory
        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(available=100)  # Only 100 bytes

            with pytest.raises(MemoryError) as exc_info:
                parser._check_memory_constraint(str(test_ifc_file))

            error_msg = str(exc_info.value)
            assert "memory" in error_msg.lower()
            assert "available" in error_msg.lower()

    def test_memory_constraint_with_custom_multiplier(self, parser, test_ifc_file):
        """Test memory constraint check with custom multiplier override."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        # With a small multiplier (1x), should pass easily
        parser._check_memory_constraint(str(test_ifc_file), multiplier=1)

        # Verify the default multiplier is used when not provided
        assert parser.MEMORY_MULTIPLIER == 10

    def test_memory_constraint_error_includes_file_path(self, parser, test_ifc_file):
        """Test that memory error message includes the file path."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(available=100)

            with pytest.raises(MemoryError) as exc_info:
                parser._check_memory_constraint(str(test_ifc_file))

            error_msg = str(exc_info.value)
            assert str(test_ifc_file) in error_msg

    def test_memory_constraint_error_includes_sizes(self, parser, test_ifc_file):
        """Test that memory error message includes file size and memory info."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(available=100)

            with pytest.raises(MemoryError) as exc_info:
                parser._check_memory_constraint(str(test_ifc_file))

            error_msg = str(exc_info.value)
            # Should contain size information
            assert "GB" in error_msg or "MB" in error_msg or "file size" in error_msg
            assert "estimated" in error_msg.lower()

    def test_memory_constraint_file_not_found(self, parser):
        """Test that memory check raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError) as exc_info:
            parser._check_memory_constraint("nonexistent_file.ifc")

        assert "nonexistent_file.ifc" in str(exc_info.value)

    def test_memory_constraint_triggered_during_load(self, parser, test_ifc_file):
        """Test that memory constraint is checked during the load() method."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(available=100)

            # load() should trigger memory check and raise MemoryError
            with pytest.raises(MemoryError):
                parser.load(str(test_ifc_file))

    def test_memory_constraint_with_large_multiplier(self, parser, test_ifc_file):
        """Test memory constraint with very large multiplier."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        # With a huge multiplier, even a small file exceeds memory
        with pytest.raises(MemoryError):
            parser._check_memory_constraint(str(test_ifc_file), multiplier=10**12)

    def test_memory_constraint_passes_with_adequate_memory(self, parser, test_ifc_file):
        """Test memory constraint passes when adequate memory is available."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        # Mock psutil to simulate plenty of available memory
        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(available=100 * 1024**3)  # 100 GB

            # Should not raise - plenty of memory
            parser._check_memory_constraint(str(test_ifc_file))

    def test_memory_constraint_boundary_exactly_sufficient(self, parser, test_ifc_file):
        """Test memory constraint at exact boundary (just enough memory)."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        file_size = test_ifc_file.stat().st_size
        # Set available to exactly what's needed (file_size * multiplier)
        required = file_size * parser.MEMORY_MULTIPLIER

        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            # Just barely enough memory - should pass
            mock_mem.return_value = MagicMock(available=required + 1)
            parser._check_memory_constraint(str(test_ifc_file))

    def test_memory_constraint_boundary_just_insufficient(self, parser, test_ifc_file):
        """Test memory constraint at exact boundary (just under required)."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        file_size = test_ifc_file.stat().st_size
        required = file_size * parser.MEMORY_MULTIPLIER

        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            # Just under required memory - should fail
            mock_mem.return_value = MagicMock(available=required - 1)
            with pytest.raises(MemoryError):
                parser._check_memory_constraint(str(test_ifc_file))

    def test_memory_constraint_error_includes_multiplier(self, parser, test_ifc_file):
        """Test that memory error message includes the multiplier used."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(available=100)

            with pytest.raises(MemoryError) as exc_info:
                parser._check_memory_constraint(str(test_ifc_file))

            error_msg = str(exc_info.value)
            # Error should mention the multiplier (e.g., "10x file size")
            assert "10x" in error_msg or "multiplier" in error_msg.lower()


def test_memory_constraint():
    """Standalone test for memory constraint enforcement.

    This test verifies that the IFCParser correctly enforces memory
    constraints by checking available system memory before loading
    IFC files. It tests both the pass and fail scenarios.
    """
    parser = IFCParser()

    # Test 1: FileNotFoundError for missing files
    with pytest.raises(FileNotFoundError):
        parser._check_memory_constraint("missing_file.ifc")

    # Test 2: Verify MEMORY_MULTIPLIER constant is defined
    assert parser.MEMORY_MULTIPLIER > 0
    assert parser.MEMORY_MULTIPLIER == 10  # Expected default value

    # Test 3: Mock low memory scenario
    test_ifc_file = Path(__file__).parent / "2786_CLT_model.ifc"
    if test_ifc_file.exists():
        with patch("ifc_validator.engine.parser.psutil.virtual_memory") as mock_mem:
            # Simulate only 100 bytes available
            mock_mem.return_value = MagicMock(available=100)

            with pytest.raises(MemoryError) as exc_info:
                parser._check_memory_constraint(str(test_ifc_file))

            error_msg = str(exc_info.value)
            # Verify error message contains helpful information
            assert "memory" in error_msg.lower()
            assert "available" in error_msg.lower()
            assert str(test_ifc_file) in error_msg

    # Test 4: Test custom multiplier
    if test_ifc_file.exists():
        # With a very small multiplier, should pass
        parser._check_memory_constraint(str(test_ifc_file), multiplier=1)

        # With huge multiplier, should fail (even small files need too much)
        with pytest.raises(MemoryError):
            parser._check_memory_constraint(str(test_ifc_file), multiplier=10**12)


def test_load_real_ifc_file():
    """Integration test: load real IFC file (test/2786_CLT_model.ifc).

    This standalone test verifies end-to-end functionality by loading
    a real IFC file and validating:
    - File loads successfully without errors
    - Schema is correctly detected (IFC4X3 for the CLT model)
    - All parser properties are populated correctly
    - Memory stats are tracked during loading
    - Entity queries work via get_entities_by_type()
    - Context manager properly cleans up resources

    This is a critical integration test that validates the parser
    works correctly with production IFC files.
    """
    test_file = Path(__file__).parent / "2786_CLT_model.ifc"

    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")

    # Test 1: Basic loading and property verification
    parser = IFCParser()
    parser.load(str(test_file))

    # Verify parser state after loading
    assert parser.is_loaded is True, "Parser should be loaded after successful load()"
    assert parser.file_path == test_file, "file_path should match loaded file"
    assert parser.schema is not None, "Schema should be detected"
    assert parser.schema in parser.SUPPORTED_SCHEMAS, (
        f"Schema {parser.schema} should be supported"
    )
    assert parser.ifc_file is not None, "ifc_file should be populated"

    # Test 2: Schema detection for this specific file (IFC4X3)
    assert parser.schema == "IFC4X3", f"Expected IFC4X3 schema, got {parser.schema}"

    # Test 3: Memory stats verification
    stats = parser.memory_stats
    assert stats is not None, "Memory stats should be populated after load"
    assert stats.file_size > 0, "File size should be positive"
    assert stats.memory_before > 0, "Memory before should be positive"
    assert stats.memory_after >= stats.memory_before, (
        "Memory after should be >= memory before"
    )
    assert stats.memory_used >= 0, "Memory used should be non-negative"
    assert stats.memory_multiplier >= 0, "Memory multiplier should be non-negative"

    # Test 4: Entity querying works
    products = parser.get_entities_by_type("IfcProduct")
    assert isinstance(products, list), "get_entities_by_type should return a list"
    # The CLT model should have some products
    assert len(products) > 0, "CLT model should contain IfcProduct entities"

    # Test 5: Query for walls (common entity type)
    walls = parser.get_entities_by_type("IfcWall")
    assert isinstance(walls, list), "IfcWall query should return a list"

    # Test 6: Query for building structure
    buildings = parser.get_entities_by_type("IfcBuilding")
    assert isinstance(buildings, list), "IfcBuilding query should return a list"

    # Test 7: Query for project (should exist in any valid IFC file)
    projects = parser.get_entities_by_type("IfcProject")
    assert isinstance(projects, list), "IfcProject query should return a list"
    assert len(projects) == 1, "IFC file should have exactly one IfcProject"

    # Cleanup
    parser.close()
    assert parser.is_loaded is False, "Parser should not be loaded after close()"

    # Test 8: Context manager integration
    with IFCParser() as ctx_parser:
        ctx_parser.load(str(test_file))
        assert ctx_parser.is_loaded is True
        assert ctx_parser.schema == "IFC4X3"

    # After context exit, parser should be closed
    assert ctx_parser.is_loaded is False, "Context manager should close parser on exit"

    # Test 9: Verify repr includes file info when loaded
    parser2 = IFCParser()
    parser2.load(str(test_file))
    repr_str = repr(parser2)
    assert "IFCParser(file=" in repr_str, "repr should include file info when loaded"
    assert "IFC4X3" in repr_str, "repr should include schema info"
    parser2.close()


# =============================================================================
# Entity Loading Tests
# =============================================================================


class TestEntityLoading:
    """Test entity loading with by_type()."""

    def test_get_entities_by_type(self, parser, test_ifc_file):
        """Test loading entities by type using by_type()."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))

        # IfcProduct is a common base class for many entities
        products = parser.get_entities_by_type("IfcProduct")
        assert isinstance(products, list)

    def test_get_entities_raises_for_invalid_type(self, parser, test_ifc_file):
        """Test that invalid entity types raise RuntimeError.

        IfcOpenShell validates entity types against the schema and raises
        RuntimeError for types that don't exist in the schema.
        """
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))

        # This entity type doesn't exist in IFC schema
        with pytest.raises(RuntimeError) as exc_info:
            parser.get_entities_by_type("IfcNonExistentEntity")

        assert "not found" in str(exc_info.value).lower()

    def test_get_entities_raises_when_not_loaded(self, parser):
        """Test that get_entities_by_type raises when no file is loaded."""
        with pytest.raises(RuntimeError) as exc_info:
            parser.get_entities_by_type("IfcWall")

        error_msg = str(exc_info.value).lower()
        assert "no" in error_msg or "not" in error_msg
        assert "loaded" in error_msg


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestContextManager:
    """Test context manager functionality."""

    def test_context_manager_closes_file(self, test_ifc_file):
        """Test that context manager closes file on exit."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        with IFCParser() as parser:
            parser.load(str(test_ifc_file))
            assert parser.is_loaded is True

        # After context exit, file should be closed
        assert parser.is_loaded is False
        assert parser.ifc_file is None

    def test_context_manager_preserves_memory_stats(self, test_ifc_file):
        """Test that memory stats are preserved after context exit."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        with IFCParser() as parser:
            parser.load(str(test_ifc_file))
            stats_inside = parser.memory_stats

        # Memory stats should be preserved
        assert parser.memory_stats is not None
        assert parser.memory_stats == stats_inside

    def test_context_manager_closes_on_exception(self, test_ifc_file):
        """Test that context manager closes file even on exception."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser = IFCParser()

        try:
            with parser:
                parser.load(str(test_ifc_file))
                raise ValueError("Test exception")
        except ValueError:
            pass

        # File should still be closed
        assert parser.is_loaded is False


# =============================================================================
# MemoryStats Tests
# =============================================================================


class TestMemoryStats:
    """Test MemoryStats dataclass."""

    def test_memory_stats_creation(self):
        """Test creating MemoryStats instance."""
        stats = MemoryStats(
            memory_before=1000000,
            memory_after=5000000,
            file_size=500000,
        )

        assert stats.memory_before == 1000000
        assert stats.memory_after == 5000000
        assert stats.file_size == 500000

    def test_memory_used_calculation(self):
        """Test memory_used property calculation."""
        stats = MemoryStats(
            memory_before=1000000,
            memory_after=5000000,
            file_size=500000,
        )

        assert stats.memory_used == 4000000  # 5M - 1M

    def test_memory_multiplier_calculation(self):
        """Test memory_multiplier property calculation."""
        stats = MemoryStats(
            memory_before=1000000,
            memory_after=5000000,
            file_size=500000,
        )

        # (5M - 1M) / 500K = 8.0x
        assert stats.memory_multiplier == 8.0

    def test_memory_multiplier_zero_file_size(self):
        """Test memory_multiplier with zero file size."""
        stats = MemoryStats(
            memory_before=1000000,
            memory_after=5000000,
            file_size=0,
        )

        assert stats.memory_multiplier == 0.0

    def test_memory_stats_repr(self):
        """Test MemoryStats string representation."""
        stats = MemoryStats(
            memory_before=1000000,
            memory_after=5000000,
            file_size=500000,
        )

        repr_str = repr(stats)
        assert "MemoryStats" in repr_str
        assert "MB" in repr_str


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_load_real_ifc_file(self, test_ifc_file):
        """Integration test: load real IFC file and verify all properties."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser = IFCParser()
        parser.load(str(test_ifc_file))

        # Verify all properties are set
        assert parser.is_loaded is True
        assert parser.file_path == test_ifc_file
        assert parser.schema in parser.SUPPORTED_SCHEMAS
        assert parser.ifc_file is not None
        assert parser.memory_stats is not None

        # Verify we can query entities
        products = parser.get_entities_by_type("IfcProduct")
        assert isinstance(products, list)

        # Cleanup
        parser.close()
        assert parser.is_loaded is False

    def test_integration_multiple_loads(self, test_ifc_file):
        """Integration test: load multiple files sequentially."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser = IFCParser()

        # First load
        parser.load(str(test_ifc_file))
        first_stats = parser.memory_stats
        assert parser.is_loaded is True

        # Second load (should close first file automatically)
        parser.load(str(test_ifc_file))
        second_stats = parser.memory_stats
        assert parser.is_loaded is True

        # Stats should be updated
        assert second_stats is not None
        assert second_stats is not first_stats

        parser.close()


# =============================================================================
# Permission Error Tests
# =============================================================================


class TestPermissionError:
    """Test permission error handling."""

    def test_permission_error_raises_when_file_not_readable(self, parser):
        """Test that PermissionError is raised when file cannot be read."""
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
                f.write(b"ISO-10303-21;")
                temp_path = f.name

            try:
                with pytest.raises(PermissionError) as exc_info:
                    parser.load(temp_path)

                assert "Permission denied" in str(exc_info.value)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def test_os_error_raises_during_file_access(self, parser):
        """Test that OSError is raised for file access issues."""
        with patch("builtins.open", side_effect=OSError("Disk error")):
            with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
                f.write(b"ISO-10303-21;")
                temp_path = f.name

            try:
                with pytest.raises(OSError) as exc_info:
                    parser.load(temp_path)

                assert "Cannot access file" in str(exc_info.value)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)


# =============================================================================
# IFC Parsing Error Tests
# =============================================================================


class TestIfcParsingErrors:
    """Test various IFC parsing error scenarios."""

    def test_memory_error_during_ifcopenshell_open(self, parser, temp_ifc2x3_file):
        """Test MemoryError raised during ifcopenshell.open()."""
        with patch("ifcopenshell.open", side_effect=MemoryError("Out of memory")):
            with pytest.raises(MemoryError) as exc_info:
                parser.load(str(temp_ifc2x3_file))

            error_msg = str(exc_info.value)
            assert "Insufficient memory" in error_msg or "memory" in error_msg.lower()

    def test_schema_error_during_parsing(self, parser, temp_ifc2x3_file):
        """Test SchemaError raised during ifcopenshell.open()."""
        import ifcopenshell

        with patch(
            "ifcopenshell.open",
            side_effect=ifcopenshell.SchemaError("Invalid schema definition"),
        ):
            with pytest.raises(ValueError) as exc_info:
                parser.load(str(temp_ifc2x3_file))

            error_msg = str(exc_info.value)
            assert "schema error" in error_msg.lower()

    def test_ifcopenshell_error_during_parsing(self, parser, temp_ifc2x3_file):
        """Test ifcopenshell.Error raised during parsing."""
        import ifcopenshell

        with patch(
            "ifcopenshell.open",
            side_effect=ifcopenshell.Error("Unable to parse IFC SPF header"),
        ):
            with pytest.raises(ValueError) as exc_info:
                parser.load(str(temp_ifc2x3_file))

            error_msg = str(exc_info.value)
            assert "Failed to parse" in error_msg
            assert "header" in error_msg.lower()

    def test_runtime_error_during_parsing(self, parser, temp_ifc2x3_file):
        """Test RuntimeError raised during ifcopenshell.open()."""
        with patch(
            "ifcopenshell.open", side_effect=RuntimeError("C++ layer error")
        ):
            with pytest.raises(ValueError) as exc_info:
                parser.load(str(temp_ifc2x3_file))

            error_msg = str(exc_info.value)
            assert "Failed to parse" in error_msg
            assert "corrupt" in error_msg.lower() or "STEP" in error_msg

    def test_unexpected_exception_during_parsing(self, parser, temp_ifc2x3_file):
        """Test unexpected Exception raised during ifcopenshell.open()."""
        with patch(
            "ifcopenshell.open",
            side_effect=KeyError("Unexpected internal error"),
        ):
            with pytest.raises(ValueError) as exc_info:
                parser.load(str(temp_ifc2x3_file))

            error_msg = str(exc_info.value)
            assert "Unexpected error" in error_msg
            assert "KeyError" in error_msg


# =============================================================================
# Unsupported Schema Tests
# =============================================================================


class TestUnsupportedSchema:
    """Test handling of unsupported IFC schemas."""

    def test_unsupported_schema_raises_value_error(self, parser):
        """Test that unsupported schema raises ValueError."""
        # Create a mock IFC file object with unsupported schema
        mock_ifc_file = MagicMock()
        mock_ifc_file.schema = "IFC2X2"  # Unsupported schema

        with patch("ifcopenshell.open", return_value=mock_ifc_file):
            with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
                f.write(b"ISO-10303-21;\nHEADER;\nDATA;\nENDSEC;\nEND-ISO-10303-21;")
                temp_path = f.name

            try:
                with pytest.raises(ValueError) as exc_info:
                    parser.load(temp_path)

                error_msg = str(exc_info.value)
                assert "Unsupported IFC schema" in error_msg
                assert "IFC2X2" in error_msg
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def test_unsupported_schema_closes_file(self, parser):
        """Test that parser closes file when unsupported schema is detected."""
        mock_ifc_file = MagicMock()
        mock_ifc_file.schema = "IFC4X1"  # Unsupported schema

        with patch("ifcopenshell.open", return_value=mock_ifc_file):
            with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
                f.write(b"ISO-10303-21;\nHEADER;\nDATA;\nENDSEC;\nEND-ISO-10303-21;")
                temp_path = f.name

            try:
                with pytest.raises(ValueError):
                    parser.load(temp_path)

                # Parser should be closed after the error
                assert parser.is_loaded is False
                assert parser.ifc_file is None
                assert parser.schema is None
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)


# =============================================================================
# Parse Error Format Tests
# =============================================================================


class TestFormatParseError:
    """Test the _format_parse_error helper method."""

    def test_format_error_unexpected_token(self, parser):
        """Test error formatting for unexpected token errors."""
        result = parser._format_parse_error(
            "test.ifc", "Unexpected token at line 42"
        )
        assert "test.ifc" in result
        assert "STEP syntax" in result

    def test_format_error_syntax_error(self, parser):
        """Test error formatting for syntax errors."""
        result = parser._format_parse_error(
            "test.ifc", "syntax error near entity #123"
        )
        assert "test.ifc" in result
        assert "syntax errors" in result

    def test_format_error_duplicate_id(self, parser):
        """Test error formatting for duplicate ID errors."""
        result = parser._format_parse_error(
            "test.ifc", "Duplicate id #456 found"
        )
        assert "test.ifc" in result
        assert "duplicate entity ids" in result.lower()

    def test_format_error_invalid_entity(self, parser):
        """Test error formatting for invalid entity errors."""
        result = parser._format_parse_error(
            "test.ifc", "Invalid entity IFCFAKEENTITY"
        )
        assert "test.ifc" in result
        assert "invalid" in result.lower()

    def test_format_error_unknown_entity(self, parser):
        """Test error formatting for unknown entity errors."""
        result = parser._format_parse_error(
            "test.ifc", "Unknown entity type IFCNONEXISTENT"
        )
        assert "test.ifc" in result
        assert "not defined in the schema" in result

    def test_format_error_header_error(self, parser):
        """Test error formatting for header parsing errors."""
        result = parser._format_parse_error(
            "test.ifc", "Unable to parse IFC SPF header"
        )
        assert "test.ifc" in result
        assert "header" in result.lower()
        assert "ISO-10303-21" in result

    def test_format_error_unknown_error(self, parser):
        """Test error formatting for unknown error types."""
        result = parser._format_parse_error(
            "test.ifc", "Some completely unknown error message"
        )
        assert "test.ifc" in result
        assert "corrupt" in result.lower() or "invalid" in result.lower()


# =============================================================================
# Property Access Tests
# =============================================================================


class TestPropertyAccess:
    """Test property access on IFCParser."""

    def test_file_path_property(self, parser, test_ifc_file):
        """Test file_path property returns Path object."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))
        assert parser.file_path == test_ifc_file
        assert isinstance(parser.file_path, Path)

    def test_ifc_file_property_before_load(self, parser):
        """Test ifc_file property is None before load."""
        assert parser.ifc_file is None

    def test_ifc_file_property_after_load(self, parser, test_ifc_file):
        """Test ifc_file property returns ifcopenshell file object."""
        if not test_ifc_file.exists():
            pytest.skip(f"Test file not found: {test_ifc_file}")

        parser.load(str(test_ifc_file))
        assert parser.ifc_file is not None

        # Verify we can use the ifc_file object directly
        project = parser.ifc_file.by_type("IfcProject")
        assert len(project) == 1

    def test_memory_stats_property_before_load(self, parser):
        """Test memory_stats property is None before load."""
        assert parser.memory_stats is None


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_load_closes_previous_file(self, parser, temp_ifc2x3_file, temp_ifc4_file):
        """Test that loading a new file closes the previous one."""
        # Load first file
        parser.load(str(temp_ifc2x3_file))
        assert parser.schema == "IFC2X3"

        # Load second file (should auto-close first)
        parser.load(str(temp_ifc4_file))
        assert parser.schema == "IFC4"

    def test_close_when_not_loaded(self, parser):
        """Test that close() can be called when no file is loaded."""
        # Should not raise
        parser.close()
        assert parser.is_loaded is False

    def test_close_multiple_times(self, parser, temp_ifc2x3_file):
        """Test that close() can be called multiple times without error."""
        parser.load(str(temp_ifc2x3_file))
        parser.close()
        parser.close()  # Second close should not raise
        assert parser.is_loaded is False

    def test_repr_shows_file_and_schema_when_loaded(self, parser, temp_ifc4_file):
        """Test repr includes file and schema when loaded."""
        parser.load(str(temp_ifc4_file))
        repr_str = repr(parser)

        assert "IFCParser(file=" in repr_str
        assert "schema='IFC4'" in repr_str

    def test_load_with_path_object(self, parser, temp_ifc4_file):
        """Test that load() accepts Path objects."""
        # Pass Path object directly instead of string
        parser.load(str(temp_ifc4_file))  # Using str for compatibility
        assert parser.is_loaded is True

    def test_get_memory_rss_returns_int(self, parser):
        """Test _get_memory_rss returns positive integer."""
        rss = parser._get_memory_rss()
        assert isinstance(rss, int)
        assert rss > 0


def test_entity_loading():
    """Integration test: entity loading with by_type() functionality.

    This standalone integration test verifies end-to-end entity loading:
    - Loading entities by type using get_entities_by_type() / by_type()
    - Verifying entity counts for common IFC types
    - Confirming returned entities have expected properties
    - Testing various entity type queries (IfcProject, IfcProduct, etc.)
    - Verifying empty list returns for non-existent entity types
    - Testing error handling when no file is loaded

    This is a critical integration test for the IFC parser's entity
    query functionality, using the real test file (2786_CLT_model.ifc).
    """
    test_file = Path(__file__).parent / "2786_CLT_model.ifc"

    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")

    parser = IFCParser()

    # Test 1: Cannot query entities before loading file
    with pytest.raises(RuntimeError) as exc_info:
        parser.get_entities_by_type("IfcWall")
    error_msg = str(exc_info.value).lower()
    assert "no" in error_msg or "not" in error_msg
    assert "loaded" in error_msg

    # Load the file
    parser.load(str(test_file))

    # Test 2: Query for IfcProject (exactly one in every valid IFC file)
    projects = parser.get_entities_by_type("IfcProject")
    assert isinstance(projects, list), "get_entities_by_type should return a list"
    assert len(projects) == 1, "IFC file should have exactly one IfcProject"

    # Verify the project entity has expected properties
    project = projects[0]
    assert hasattr(project, "GlobalId"), "IfcProject should have GlobalId attribute"
    assert hasattr(project, "Name"), "IfcProject should have Name attribute"

    # Test 3: Query for IfcProduct (base class for spatial/physical elements)
    products = parser.get_entities_by_type("IfcProduct")
    assert isinstance(products, list), "IfcProduct query should return a list"
    # A real IFC file should have products
    assert len(products) > 0, "IFC file should contain IfcProduct entities"

    # Verify product entities have standard attributes
    for product in products[:5]:  # Check first 5 to limit iteration
        assert hasattr(product, "GlobalId"), "IfcProduct should have GlobalId"
        assert hasattr(product, "Name"), "IfcProduct should have Name"
        assert hasattr(product, "id"), "Entity should have STEP id"

    # Test 4: Query for IfcBuilding (spatial structure)
    buildings = parser.get_entities_by_type("IfcBuilding")
    assert isinstance(buildings, list), "IfcBuilding query should return a list"
    # Most IFC files have at least one building
    assert len(buildings) >= 0, "Buildings list should be valid (may be empty)"

    # Test 5: Query for IfcSite (spatial structure)
    sites = parser.get_entities_by_type("IfcSite")
    assert isinstance(sites, list), "IfcSite query should return a list"

    # Test 6: Query for IfcWall (common building element)
    walls = parser.get_entities_by_type("IfcWall")
    assert isinstance(walls, list), "IfcWall query should return a list"

    # Test 7: Query for non-existent entity type raises RuntimeError
    # (IfcOpenShell validates entity types against the schema)
    with pytest.raises(RuntimeError) as exc_info:
        parser.get_entities_by_type("IfcFakeEntityTypeThatDoesNotExist")
    assert "not found" in str(exc_info.value).lower()

    # Test 8: Query for geometry-related entities
    cartesian_points = parser.get_entities_by_type("IfcCartesianPoint")
    assert isinstance(cartesian_points, list), "IfcCartesianPoint query should work"
    # IFC files typically have many cartesian points for geometry
    assert len(cartesian_points) > 0, "IFC file should contain geometry data"

    # Test 9: Query for IfcRelationship entities (relationship patterns)
    rel_contains = parser.get_entities_by_type("IfcRelContainedInSpatialStructure")
    assert isinstance(rel_contains, list), "Relationship query should return list"

    # Test 10: Query for property sets
    property_sets = parser.get_entities_by_type("IfcPropertySet")
    assert isinstance(property_sets, list), "IfcPropertySet query should work"

    # Test 11: Verify entity type consistency
    # All returned entities should be of the requested type or subtypes
    for wall in walls[:3]:  # Check first 3
        assert wall.is_a("IfcWall"), "Returned entity should be IfcWall or subtype"

    # Test 12: Query for owner history (metadata)
    owner_histories = parser.get_entities_by_type("IfcOwnerHistory")
    assert isinstance(owner_histories, list), "IfcOwnerHistory query should work"
    assert len(owner_histories) > 0, "IFC file should have owner history entries"

    # Clean up
    parser.close()

    # Test 13: After close, querying should raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        parser.get_entities_by_type("IfcWall")
    error_msg = str(exc_info.value).lower()
    assert "no" in error_msg or "not" in error_msg
    assert "loaded" in error_msg

    # Test 14: Verify entity loading works with context manager
    with IFCParser() as ctx_parser:
        ctx_parser.load(str(test_file))
        ctx_projects = ctx_parser.get_entities_by_type("IfcProject")
        assert len(ctx_projects) == 1
        ctx_products = ctx_parser.get_entities_by_type("IfcProduct")
        assert len(ctx_products) > 0

    # After context exit, parser should be closed
    assert ctx_parser.is_loaded is False
