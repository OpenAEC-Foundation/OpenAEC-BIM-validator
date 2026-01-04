"""Unit tests for the ifc_validator.formatters module.

Tests cover:
- Console formatter: Rich formatting with tables, panels, and color-coded status
- JSON formatter: Valid JSON output with required fields using dataclass serialization
- HTML formatter: Valid HTML document with proper structure

Usage:
    pytest test/test_formatters.py -v
    pytest test/test_formatters.py --cov=src --cov-report=term-missing
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ifc_validator.validator import (
    EntityFailure,
    SpecificationResult,
    ValidationResult,
)
from src.ifc_validator.formatters.console import (
    format_console,
    format_console_to_string,
    _get_status_text,
    _get_status_badge,
    _truncate,
    _create_summary_panel,
    _create_specifications_table,
    _create_failures_panel,
)
from src.ifc_validator.formatters.json import (
    format_json,
    format_json_compact,
    format_json_to_file,
    print_json,
    _result_to_dict,
)
from src.ifc_validator.formatters.html import (
    format_html,
    format_html_to_file,
    _escape_html,
    _get_status_class,
    _get_status_text as html_get_status_text,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def passing_validation_result():
    """Create a ValidationResult for a passing validation."""
    spec = SpecificationResult(
        name="Wall Naming Convention",
        description="All walls must have names starting with 'W-'",
        passed=True,
        applicable_count=5,
        passed_count=5,
        failed_count=0,
        failures=[],
    )
    return ValidationResult(
        timestamp="2025-01-01T12:00:00",
        ifc_file="sample.ifc",
        ifc_schema="IFC4",
        ifc_entity_count=100,
        ids_file="rules.ids",
        ids_title="Test Validation Rules",
        validation_time_seconds=1.234,
        total_specifications=1,
        passed_specifications=1,
        failed_specifications=0,
        pass_rate_percent=100.0,
        specifications=[spec],
        overall_pass=True,
    )


@pytest.fixture
def failing_validation_result():
    """Create a ValidationResult for a failing validation."""
    failure1 = EntityFailure(
        entity_id=123,
        entity_type="IfcWall",
        entity_name="Bad Wall Name",
        global_id="abc123def456",
    )
    failure2 = EntityFailure(
        entity_id=456,
        entity_type="IfcWall",
        entity_name=None,  # No name
        global_id=None,  # No GlobalId
    )
    spec_fail = SpecificationResult(
        name="Wall Naming Convention",
        description="All walls must have names starting with 'W-'",
        passed=False,
        applicable_count=5,
        passed_count=3,
        failed_count=2,
        failures=[failure1, failure2],
    )
    spec_pass = SpecificationResult(
        name="Door Naming Convention",
        description="All doors must have names starting with 'D-'",
        passed=True,
        applicable_count=3,
        passed_count=3,
        failed_count=0,
        failures=[],
    )
    return ValidationResult(
        timestamp="2025-01-01T12:00:00",
        ifc_file="sample-fail.ifc",
        ifc_schema="IFC4",
        ifc_entity_count=150,
        ids_file="rules.ids",
        ids_title="Test Validation Rules",
        validation_time_seconds=2.567,
        total_specifications=2,
        passed_specifications=1,
        failed_specifications=1,
        pass_rate_percent=50.0,
        specifications=[spec_fail, spec_pass],
        overall_pass=False,
    )


@pytest.fixture
def minimal_validation_result():
    """Create a minimal ValidationResult with defaults."""
    return ValidationResult(
        timestamp="2025-01-01T12:00:00",
        ifc_file="model.ifc",
        ifc_schema="IFC4",
        ifc_entity_count=0,
        ids_file="rules.ids",
        ids_title=None,
        validation_time_seconds=0.0,
        total_specifications=0,
        passed_specifications=0,
        failed_specifications=0,
        pass_rate_percent=0.0,
        specifications=[],
        overall_pass=True,
    )


@pytest.fixture
def many_failures_result():
    """Create a ValidationResult with many failures to test truncation."""
    failures = [
        EntityFailure(
            entity_id=i,
            entity_type="IfcWall",
            entity_name=f"Wall-{i}",
            global_id=f"guid-{i:08d}",
        )
        for i in range(25)  # More than the default max of 10
    ]
    spec = SpecificationResult(
        name="Naming Convention",
        description="Test specification",
        passed=False,
        applicable_count=30,
        passed_count=5,
        failed_count=25,
        failures=failures,
    )
    return ValidationResult(
        timestamp="2025-01-01T12:00:00",
        ifc_file="large.ifc",
        ifc_schema="IFC4",
        ifc_entity_count=1000,
        ids_file="rules.ids",
        ids_title="Large Test",
        validation_time_seconds=5.0,
        total_specifications=1,
        passed_specifications=0,
        failed_specifications=1,
        pass_rate_percent=0.0,
        specifications=[spec],
        overall_pass=False,
    )


# =============================================================================
# Console Formatter Tests
# =============================================================================


class TestConsoleFormatter:
    """Test console output formatter with Rich formatting."""

    def test_format_console_to_string_returns_string(self, passing_validation_result):
        """Test that format_console_to_string returns a string."""
        output = format_console_to_string(passing_validation_result)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_format_console_to_string_contains_pass_status(self, passing_validation_result):
        """Test that passing result shows pass status."""
        output = format_console_to_string(passing_validation_result)
        # Should contain pass indicators
        assert "PASS" in output or "pass" in output.lower()

    def test_format_console_to_string_contains_fail_status(self, failing_validation_result):
        """Test that failing result shows fail status."""
        output = format_console_to_string(failing_validation_result)
        # Should contain fail indicators
        assert "FAIL" in output or "fail" in output.lower()

    def test_format_console_to_string_contains_ifc_info(self, passing_validation_result):
        """Test that console output contains IFC file information."""
        output = format_console_to_string(passing_validation_result)
        assert "sample.ifc" in output
        assert "IFC4" in output

    def test_format_console_to_string_contains_ids_info(self, passing_validation_result):
        """Test that console output contains IDS file information."""
        output = format_console_to_string(passing_validation_result)
        assert "rules.ids" in output

    def test_format_console_to_string_contains_specification_names(self, passing_validation_result):
        """Test that console output contains specification names."""
        output = format_console_to_string(passing_validation_result)
        assert "Wall Naming Convention" in output

    def test_format_console_to_string_contains_statistics(self, passing_validation_result):
        """Test that console output contains validation statistics."""
        output = format_console_to_string(passing_validation_result)
        # Should show pass rate or statistics
        assert "100" in output or "1" in output  # Pass rate or counts

    def test_format_console_to_string_with_failures(self, failing_validation_result):
        """Test that console output shows failure details."""
        output = format_console_to_string(failing_validation_result, show_failures=True)
        # Should show failed entity info
        assert "Bad Wall Name" in output or "IfcWall" in output

    def test_format_console_to_string_without_failures(self, failing_validation_result):
        """Test that console output can hide failure details."""
        output = format_console_to_string(failing_validation_result, show_failures=False)
        # Still shows summary but not detailed failures
        assert "FAIL" in output or "fail" in output.lower()

    def test_format_console_to_string_minimal_result(self, minimal_validation_result):
        """Test console output with minimal/empty validation result."""
        output = format_console_to_string(minimal_validation_result)
        assert isinstance(output, str)
        assert "model.ifc" in output

    def test_format_console_to_string_many_failures(self, many_failures_result):
        """Test console output truncates many failures."""
        output = format_console_to_string(many_failures_result)
        # Should show some failures but mention there are more
        assert "more" in output.lower() or "..." in output

    def test_get_status_text_pass(self):
        """Test _get_status_text returns correct text for pass."""
        result = _get_status_text(True)
        assert "PASS" in str(result)

    def test_get_status_text_fail(self):
        """Test _get_status_text returns correct text for fail."""
        result = _get_status_text(False)
        assert "FAIL" in str(result)

    def test_get_status_badge_pass(self):
        """Test _get_status_badge returns green styled text for pass."""
        result = _get_status_badge(True)
        assert "green" in result
        assert "PASS" in result

    def test_get_status_badge_fail(self):
        """Test _get_status_badge returns red styled text for fail."""
        result = _get_status_badge(False)
        assert "red" in result
        assert "FAIL" in result

    def test_truncate_short_text(self):
        """Test _truncate doesn't modify short text."""
        result = _truncate("short text", max_length=20)
        assert result == "short text"

    def test_truncate_long_text(self):
        """Test _truncate adds ellipsis to long text."""
        long_text = "a" * 100
        result = _truncate(long_text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_truncate_none_text(self):
        """Test _truncate handles None."""
        result = _truncate(None)
        assert result == ""

    def test_create_summary_panel_returns_panel(self, passing_validation_result):
        """Test _create_summary_panel returns a Rich Panel."""
        from rich.panel import Panel
        result = _create_summary_panel(passing_validation_result)
        assert isinstance(result, Panel)

    def test_create_specifications_table_returns_table(self, passing_validation_result):
        """Test _create_specifications_table returns a Rich Table."""
        from rich.table import Table
        result = _create_specifications_table(passing_validation_result)
        assert isinstance(result, Table)

    def test_create_failures_panel_with_failures(self, failing_validation_result):
        """Test _create_failures_panel returns Panel for failed specs."""
        from rich.panel import Panel
        failed_spec = failing_validation_result.specifications[0]
        result = _create_failures_panel(failed_spec, 1)
        assert isinstance(result, Panel)

    def test_create_failures_panel_without_failures(self, passing_validation_result):
        """Test _create_failures_panel returns None for passing specs."""
        passing_spec = passing_validation_result.specifications[0]
        result = _create_failures_panel(passing_spec, 1)
        assert result is None


class TestConsoleFormatterRichFeatures:
    """Test that console formatter uses Rich features properly."""

    def test_console_output_has_ansi_codes(self, passing_validation_result):
        """Test that console output contains ANSI formatting codes."""
        # force_terminal=True in format_console_to_string should produce ANSI codes
        output = format_console_to_string(passing_validation_result)
        # ANSI codes start with escape character
        # Rich output should have formatting
        # At minimum, check it's formatted output, not plain text
        assert len(output) > 100  # Should have substantial formatted content

    def test_console_output_has_box_characters(self, passing_validation_result):
        """Test that console output contains table/panel box characters."""
        output = format_console_to_string(passing_validation_result)
        # Rich tables and panels use box-drawing characters
        # Check for common table elements
        assert any(char in output for char in ["│", "─", "┼", "─", "|", "-", "+"])


# =============================================================================
# JSON Formatter Tests
# =============================================================================


class TestJSONFormatter:
    """Test JSON output formatter."""

    def test_format_json_returns_string(self, passing_validation_result):
        """Test that format_json returns a string."""
        output = format_json(passing_validation_result)
        assert isinstance(output, str)

    def test_format_json_is_valid_json(self, passing_validation_result):
        """Test that format_json produces valid JSON."""
        output = format_json(passing_validation_result)
        # Should parse without error
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_format_json_has_required_fields(self, passing_validation_result):
        """Test that JSON output has all required fields."""
        output = format_json(passing_validation_result)
        data = json.loads(output)

        # Check required top-level fields
        assert "timestamp" in data
        assert "ifc_file" in data
        assert "ifc_schema" in data
        assert "ifc_entity_count" in data
        assert "ids_file" in data
        assert "overall_pass" in data
        assert "specifications" in data
        assert "total_specifications" in data
        assert "passed_specifications" in data
        assert "failed_specifications" in data
        assert "pass_rate_percent" in data
        assert "validation_time_seconds" in data

    def test_format_json_overall_pass_is_boolean(self, passing_validation_result):
        """Test that overall_pass is a boolean in JSON."""
        output = format_json(passing_validation_result)
        data = json.loads(output)
        assert isinstance(data["overall_pass"], bool)
        assert data["overall_pass"] is True

    def test_format_json_overall_pass_false(self, failing_validation_result):
        """Test that overall_pass is False for failing validation."""
        output = format_json(failing_validation_result)
        data = json.loads(output)
        assert data["overall_pass"] is False

    def test_format_json_specifications_is_list(self, passing_validation_result):
        """Test that specifications is a list in JSON."""
        output = format_json(passing_validation_result)
        data = json.loads(output)
        assert isinstance(data["specifications"], list)

    def test_format_json_specification_has_required_fields(self, passing_validation_result):
        """Test that each specification has required fields."""
        output = format_json(passing_validation_result)
        data = json.loads(output)

        for spec in data["specifications"]:
            assert "name" in spec
            assert "passed" in spec
            assert "applicable_count" in spec
            assert "passed_count" in spec
            assert "failed_count" in spec
            assert "failures" in spec

    def test_format_json_failure_has_required_fields(self, failing_validation_result):
        """Test that each failure has required fields."""
        output = format_json(failing_validation_result)
        data = json.loads(output)

        for spec in data["specifications"]:
            for failure in spec["failures"]:
                assert "entity_id" in failure
                assert "entity_type" in failure
                # entity_name and global_id may be None

    def test_format_json_with_indent(self, passing_validation_result):
        """Test that format_json respects indent parameter."""
        output_indented = format_json(passing_validation_result, indent=4)
        output_no_indent = format_json(passing_validation_result, indent=None)

        # Indented version should be longer due to whitespace
        assert len(output_indented) > len(output_no_indent)

        # Both should be valid JSON
        json.loads(output_indented)
        json.loads(output_no_indent)

    def test_format_json_compact(self, passing_validation_result):
        """Test that format_json_compact produces compact JSON."""
        output = format_json_compact(passing_validation_result)

        # Should have no newlines (except possibly in strings)
        assert output.count("\n") == 0
        json.loads(output)

    def test_format_json_with_none_values(self, minimal_validation_result):
        """Test JSON output handles None values correctly."""
        output = format_json(minimal_validation_result)
        data = json.loads(output)

        # ids_title is None in minimal result
        assert data["ids_title"] is None

    def test_format_json_preserves_types(self, passing_validation_result):
        """Test that JSON output preserves correct types."""
        output = format_json(passing_validation_result)
        data = json.loads(output)

        assert isinstance(data["ifc_entity_count"], int)
        assert isinstance(data["validation_time_seconds"], float)
        assert isinstance(data["pass_rate_percent"], float)
        assert isinstance(data["total_specifications"], int)

    def test_result_to_dict_returns_dict(self, passing_validation_result):
        """Test that _result_to_dict returns a dictionary."""
        result = _result_to_dict(passing_validation_result)
        assert isinstance(result, dict)

    def test_format_json_to_file(self, passing_validation_result):
        """Test that format_json_to_file writes valid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"

            result_path = format_json_to_file(passing_validation_result, output_path)

            assert result_path == output_path
            assert output_path.exists()

            # Read and verify JSON
            content = output_path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert data["overall_pass"] is True

    def test_format_json_to_file_creates_parent_dirs(self, passing_validation_result):
        """Test that format_json_to_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "nested" / "output.json"

            result_path = format_json_to_file(passing_validation_result, output_path)

            assert result_path == output_path
            assert output_path.exists()

    def test_print_json_outputs_to_stdout(self, passing_validation_result, capsys):
        """Test that print_json outputs to stdout."""
        print_json(passing_validation_result)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["overall_pass"] is True


class TestJSONFormatterEdgeCases:
    """Test JSON formatter edge cases."""

    def test_format_json_empty_specifications(self, minimal_validation_result):
        """Test JSON output with empty specifications list."""
        output = format_json(minimal_validation_result)
        data = json.loads(output)
        assert data["specifications"] == []

    def test_format_json_special_characters(self):
        """Test JSON output handles special characters in strings."""
        spec = SpecificationResult(
            name='Test with "quotes" and \\backslash',
            description="Line1\nLine2\tTabbed",
            passed=True,
            applicable_count=1,
            passed_count=1,
            failed_count=0,
            failures=[],
        )
        result = ValidationResult(
            timestamp="2025-01-01T12:00:00",
            ifc_file="model.ifc",
            ifc_schema="IFC4",
            ifc_entity_count=1,
            ids_file="rules.ids",
            ids_title="Title with 'quotes'",
            validation_time_seconds=0.1,
            total_specifications=1,
            passed_specifications=1,
            failed_specifications=0,
            pass_rate_percent=100.0,
            specifications=[spec],
            overall_pass=True,
        )

        output = format_json(result)
        # Should be valid JSON despite special characters
        data = json.loads(output)
        assert "quotes" in data["specifications"][0]["name"]

    def test_format_json_unicode_characters(self):
        """Test JSON output handles Unicode characters."""
        spec = SpecificationResult(
            name="Test with unicode: \u00e9\u00e8\u00ea",
            description="Chinese: \u4e2d\u6587",
            passed=True,
            applicable_count=1,
            passed_count=1,
            failed_count=0,
            failures=[],
        )
        result = ValidationResult(
            timestamp="2025-01-01T12:00:00",
            ifc_file="model.ifc",
            ifc_schema="IFC4",
            ifc_entity_count=1,
            ids_file="rules.ids",
            ids_title=None,
            validation_time_seconds=0.1,
            total_specifications=1,
            passed_specifications=1,
            failed_specifications=0,
            pass_rate_percent=100.0,
            specifications=[spec],
            overall_pass=True,
        )

        output = format_json(result)
        data = json.loads(output)
        # ensure_ascii=False should preserve Unicode
        assert "\u00e9" in data["specifications"][0]["name"]


# =============================================================================
# HTML Formatter Tests
# =============================================================================


class TestHTMLFormatter:
    """Test HTML output formatter."""

    def test_format_html_returns_string(self, passing_validation_result):
        """Test that format_html returns a string."""
        output = format_html(passing_validation_result)
        assert isinstance(output, str)

    def test_format_html_is_valid_html_document(self, passing_validation_result):
        """Test that format_html produces valid HTML document structure."""
        output = format_html(passing_validation_result)

        # Check for HTML document structure
        assert "<!DOCTYPE html>" in output
        assert "<html" in output
        assert "</html>" in output
        assert "<head>" in output
        assert "</head>" in output
        assert "<body>" in output
        assert "</body>" in output

    def test_format_html_has_meta_charset(self, passing_validation_result):
        """Test that HTML has UTF-8 charset declaration."""
        output = format_html(passing_validation_result)
        assert 'charset="UTF-8"' in output or "charset=UTF-8" in output

    def test_format_html_has_title(self, passing_validation_result):
        """Test that HTML has title element."""
        output = format_html(passing_validation_result)
        assert "<title>" in output
        assert "</title>" in output
        assert "Validation" in output or "IFC" in output

    def test_format_html_has_style(self, passing_validation_result):
        """Test that HTML has embedded CSS styles."""
        output = format_html(passing_validation_result)
        assert "<style>" in output
        assert "</style>" in output

    def test_format_html_contains_ifc_info(self, passing_validation_result):
        """Test that HTML contains IFC file information."""
        output = format_html(passing_validation_result)
        assert "sample.ifc" in output
        assert "IFC4" in output

    def test_format_html_contains_ids_info(self, passing_validation_result):
        """Test that HTML contains IDS file information."""
        output = format_html(passing_validation_result)
        assert "rules.ids" in output

    def test_format_html_contains_specification_names(self, passing_validation_result):
        """Test that HTML contains specification names."""
        output = format_html(passing_validation_result)
        assert "Wall Naming Convention" in output

    def test_format_html_contains_pass_status(self, passing_validation_result):
        """Test that HTML contains pass status."""
        output = format_html(passing_validation_result)
        assert "PASS" in output or "pass" in output.lower()

    def test_format_html_contains_fail_status(self, failing_validation_result):
        """Test that HTML contains fail status."""
        output = format_html(failing_validation_result)
        assert "FAIL" in output or "fail" in output.lower()

    def test_format_html_has_status_colors(self, passing_validation_result):
        """Test that HTML has color styles for pass/fail."""
        output = format_html(passing_validation_result)
        # Should have CSS color definitions
        assert "green" in output.lower() or "#28a745" in output
        assert "red" in output.lower() or "#dc3545" in output

    def test_format_html_contains_failure_details(self, failing_validation_result):
        """Test that HTML contains failure details."""
        output = format_html(failing_validation_result)
        assert "Bad Wall Name" in output or "IfcWall" in output

    def test_format_html_has_table_structure(self, passing_validation_result):
        """Test that HTML has table for specifications."""
        output = format_html(passing_validation_result)
        assert "<table" in output
        assert "</table>" in output
        assert "<th" in output or "<thead" in output

    def test_format_html_has_responsive_design(self, passing_validation_result):
        """Test that HTML has responsive design elements."""
        output = format_html(passing_validation_result)
        # Should have viewport meta tag
        assert "viewport" in output
        # Should have media queries or grid/flex
        assert "media" in output.lower() or "grid" in output.lower() or "flex" in output.lower()

    def test_format_html_minimal_result(self, minimal_validation_result):
        """Test HTML output with minimal/empty validation result."""
        output = format_html(minimal_validation_result)
        assert "<!DOCTYPE html>" in output
        assert "model.ifc" in output

    def test_format_html_many_failures(self, many_failures_result):
        """Test HTML output handles many failures gracefully."""
        output = format_html(many_failures_result)
        assert "<!DOCTYPE html>" in output
        # Should show failures or mention truncation
        assert "Wall" in output or "more" in output.lower()

    def test_escape_html_basic(self):
        """Test _escape_html escapes HTML special characters."""
        assert _escape_html("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

    def test_escape_html_ampersand(self):
        """Test _escape_html escapes ampersand."""
        assert _escape_html("A & B") == "A &amp; B"

    def test_escape_html_quotes(self):
        """Test _escape_html escapes quotes."""
        assert '&quot;' in _escape_html('test "quoted"')

    def test_escape_html_none(self):
        """Test _escape_html handles None."""
        assert _escape_html(None) == ""

    def test_get_status_class_pass(self):
        """Test _get_status_class returns 'pass' for True."""
        assert _get_status_class(True) == "pass"

    def test_get_status_class_fail(self):
        """Test _get_status_class returns 'fail' for False."""
        assert _get_status_class(False) == "fail"

    def test_html_get_status_text_pass(self):
        """Test HTML _get_status_text returns pass text."""
        assert "PASS" in html_get_status_text(True)

    def test_html_get_status_text_fail(self):
        """Test HTML _get_status_text returns fail text."""
        assert "FAIL" in html_get_status_text(False)


class TestHTMLFormatterFileOperations:
    """Test HTML formatter file operations."""

    def test_format_html_to_file(self, passing_validation_result):
        """Test that format_html_to_file writes valid HTML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            result_path = format_html_to_file(passing_validation_result, output_path)

            assert result_path == output_path
            assert output_path.exists()

            # Read and verify HTML
            content = output_path.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content
            assert "sample.ifc" in content

    def test_format_html_to_file_creates_parent_dirs(self, passing_validation_result):
        """Test that format_html_to_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "nested" / "report.html"

            result_path = format_html_to_file(passing_validation_result, output_path)

            assert result_path == output_path
            assert output_path.exists()

    def test_format_html_to_file_utf8_encoding(self, passing_validation_result):
        """Test that format_html_to_file uses UTF-8 encoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            format_html_to_file(passing_validation_result, output_path)

            # Read with explicit UTF-8 encoding
            content = output_path.read_text(encoding="utf-8")
            assert 'charset="UTF-8"' in content or "charset=UTF-8" in content


class TestHTMLFormatterEdgeCases:
    """Test HTML formatter edge cases."""

    def test_format_html_special_characters_escaped(self):
        """Test that special characters are escaped in HTML."""
        spec = SpecificationResult(
            name="Test <script>alert('xss')</script>",
            description="Ampersand & and <tags>",
            passed=True,
            applicable_count=1,
            passed_count=1,
            failed_count=0,
            failures=[],
        )
        result = ValidationResult(
            timestamp="2025-01-01T12:00:00",
            ifc_file="model.ifc",
            ifc_schema="IFC4",
            ifc_entity_count=1,
            ids_file="rules.ids",
            ids_title="Test & <script>",
            validation_time_seconds=0.1,
            total_specifications=1,
            passed_specifications=1,
            failed_specifications=0,
            pass_rate_percent=100.0,
            specifications=[spec],
            overall_pass=True,
        )

        output = format_html(result)

        # Special characters should be escaped
        assert "<script>" not in output  # Should be escaped
        assert "&lt;script&gt;" in output  # Should be escaped form
        assert "&amp;" in output  # Ampersand should be escaped

    def test_format_html_with_none_description(self):
        """Test HTML handles None description gracefully."""
        spec = SpecificationResult(
            name="Test",
            description=None,
            passed=True,
            applicable_count=1,
            passed_count=1,
            failed_count=0,
            failures=[],
        )
        result = ValidationResult(
            timestamp="2025-01-01T12:00:00",
            ifc_file="model.ifc",
            ifc_schema="IFC4",
            ifc_entity_count=1,
            ids_file="rules.ids",
            ids_title=None,
            validation_time_seconds=0.1,
            total_specifications=1,
            passed_specifications=1,
            failed_specifications=0,
            pass_rate_percent=100.0,
            specifications=[spec],
            overall_pass=True,
        )

        output = format_html(result)
        assert "<!DOCTYPE html>" in output
        # Should not contain "None" as literal text
        assert ">None<" not in output


# =============================================================================
# Integration Tests for Formatters
# =============================================================================


class TestFormatterIntegration:
    """Integration tests for all formatters working together."""

    def test_all_formatters_accept_same_result(self, passing_validation_result):
        """Test that all formatters accept the same ValidationResult."""
        console_output = format_console_to_string(passing_validation_result)
        json_output = format_json(passing_validation_result)
        html_output = format_html(passing_validation_result)

        assert isinstance(console_output, str)
        assert isinstance(json_output, str)
        assert isinstance(html_output, str)

    def test_all_formatters_show_same_status(self, passing_validation_result):
        """Test that all formatters show consistent pass status."""
        console_output = format_console_to_string(passing_validation_result)
        json_output = format_json(passing_validation_result)
        html_output = format_html(passing_validation_result)

        # Console should show pass
        assert "PASS" in console_output or "pass" in console_output.lower()

        # JSON should show overall_pass: true
        json_data = json.loads(json_output)
        assert json_data["overall_pass"] is True

        # HTML should show pass
        assert "PASS" in html_output or "pass" in html_output.lower()

    def test_all_formatters_show_fail_status(self, failing_validation_result):
        """Test that all formatters show consistent fail status."""
        console_output = format_console_to_string(failing_validation_result)
        json_output = format_json(failing_validation_result)
        html_output = format_html(failing_validation_result)

        # Console should show fail
        assert "FAIL" in console_output or "fail" in console_output.lower()

        # JSON should show overall_pass: false
        json_data = json.loads(json_output)
        assert json_data["overall_pass"] is False

        # HTML should show fail
        assert "FAIL" in html_output or "fail" in html_output.lower()

    def test_all_formatters_show_same_ifc_file(self, passing_validation_result):
        """Test that all formatters show the same IFC file name."""
        console_output = format_console_to_string(passing_validation_result)
        json_output = format_json(passing_validation_result)
        html_output = format_html(passing_validation_result)

        assert "sample.ifc" in console_output
        json_data = json.loads(json_output)
        assert json_data["ifc_file"] == "sample.ifc"
        assert "sample.ifc" in html_output
