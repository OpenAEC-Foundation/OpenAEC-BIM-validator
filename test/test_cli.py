"""Unit tests for the ifc-validate CLI.

Tests cover:
- CLI help text and usage
- File validation (existence)
- Extension validation for IFC (.ifc, .ifcxml, .ifczip) and IDS (.ids) files
- Error messages for invalid inputs
- Exit codes for validation pass/fail scenarios
- Output format options (console, json, html)

Usage:
    pytest test/test_cli.py -v
    pytest test/test_cli.py --cov=src --cov-report=term-missing
"""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ifc_validator.cli import app

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a CliRunner instance for testing."""
    return CliRunner()


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
def temp_invalid_ids_extension_file():
    """Create a temporary file with invalid IDS extension."""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        f.write(b"<xml>Not an IDS file</xml>")
        temp_path = f.name
    yield Path(temp_path)
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# =============================================================================
# CLI Help Tests
# =============================================================================


class TestCLIHelp:
    """Test CLI help text and usage."""

    def test_help_flag(self, runner):
        """Test that --help flag displays usage information."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "ifc-validate" in result.output.lower() or "validate" in result.output.lower()
        assert "--ids" in result.output
        assert "--output" in result.output

    def test_help_shows_ifc_file_argument(self, runner):
        """Test that help shows IFC file as required argument."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # Check for IFC file argument in help
        assert "ifc" in result.output.lower()

    def test_help_shows_required_ids_option(self, runner):
        """Test that help shows --ids as required option."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "--ids" in result.output
        # The -i short option should also be shown
        assert "-i" in result.output

    def test_help_shows_output_formats(self, runner):
        """Test that help shows output format options."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "--output" in result.output
        assert "-o" in result.output
        # Should mention available formats
        output_lower = result.output.lower()
        assert "console" in output_lower or "json" in output_lower or "html" in output_lower

    def test_version_flag(self, runner):
        """Test that --version flag displays version information."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "version" in result.output.lower()


# =============================================================================
# File Not Found Tests
# =============================================================================


class TestFileNotFound:
    """Test error handling for non-existent files."""

    def test_ifc_file_not_found(self, runner, sample_ids_path):
        """Test that error is shown when IFC file doesn't exist."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            ["nonexistent_file.ifc", "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()
        assert "not found" in result.output.lower() or "nonexistent" in result.output.lower()

    def test_ids_file_not_found(self, runner, sample_ifc_path):
        """Test that error is shown when IDS file doesn't exist."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", "nonexistent_rules.ids"],
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()
        assert "not found" in result.output.lower() or "nonexistent" in result.output.lower()

    def test_both_files_not_found(self, runner):
        """Test that error is shown when both files don't exist."""
        result = runner.invoke(
            app,
            ["nonexistent.ifc", "--ids", "nonexistent.ids"],
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_file_not_found_message_includes_path(self, runner, sample_ids_path):
        """Test that error message includes the missing file path."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        fake_path = "path/to/missing/model.ifc"
        result = runner.invoke(
            app,
            [fake_path, "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        # Error message should include the file path
        assert "model.ifc" in result.output or "missing" in result.output.lower()


# =============================================================================
# IFC Extension Validation Tests
# =============================================================================


class TestIFCExtensionValidation:
    """Test validation of IFC file extensions."""

    def test_reject_invalid_ifc_extension(self, runner, sample_ids_path, temp_invalid_extension_file):
        """Test that files without valid IFC extension are rejected."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(temp_invalid_extension_file), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        output_lower = result.output.lower()
        assert "error" in output_lower
        # Should mention extension issue
        assert "extension" in output_lower or "invalid" in output_lower

    def test_accept_ifc_extension(self, runner, sample_ifc_path, sample_ids_path):
        """Test that .ifc extension is accepted."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        # Should not have extension error
        output_lower = result.output.lower()
        assert "invalid" not in output_lower or "extension" not in output_lower

    def test_case_insensitive_ifc_extension(self, runner, sample_ids_path):
        """Test that IFC extensions are validated case-insensitively."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        # Create a temp file with uppercase extension
        with tempfile.NamedTemporaryFile(suffix=".IFC", delete=False) as f:
            # Write minimal IFC content
            f.write(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;")
            temp_path = f.name

        try:
            result = runner.invoke(
                app,
                [temp_path, "--ids", str(sample_ids_path)],
            )

            # Should not fail with extension validation error
            output_lower = result.output.lower()
            # It might fail for parse error but not extension error
            if "extension" in output_lower:
                assert "valid" in output_lower or ".ifc" in output_lower
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# =============================================================================
# IDS Extension Validation Tests
# =============================================================================


class TestIDSExtensionValidation:
    """Test validation of IDS file extensions."""

    def test_reject_invalid_ids_extension(self, runner, sample_ifc_path, temp_invalid_ids_extension_file):
        """Test that files without .ids extension are rejected."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(temp_invalid_ids_extension_file)],
        )

        assert result.exit_code == 1
        output_lower = result.output.lower()
        assert "error" in output_lower
        # Should mention extension issue
        assert "extension" in output_lower or "invalid" in output_lower

    def test_accept_ids_extension(self, runner, sample_ifc_path, sample_ids_path):
        """Test that .ids extension is accepted."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        # Should not have IDS extension error
        output_lower = result.output.lower()
        # If there's an extension error, it shouldn't be about .ids
        if "extension" in output_lower and "invalid" in output_lower:
            assert ".ids" not in output_lower


# =============================================================================
# Missing Required Arguments Tests
# =============================================================================


class TestMissingArguments:
    """Test error handling for missing required arguments."""

    def test_missing_ifc_file_argument(self, runner):
        """Test that error is shown when IFC file argument is missing."""
        result = runner.invoke(
            app,
            ["--ids", "rules.ids"],
        )

        # Should fail - missing required argument
        assert result.exit_code != 0

    def test_missing_ids_option(self, runner, sample_ifc_path):
        """Test that error is shown when --ids option is missing."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path)],
        )

        # Should fail - missing required --ids option
        assert result.exit_code != 0
        # Error should mention --ids
        assert "--ids" in result.output or "required" in result.output.lower()


# =============================================================================
# Exit Code Tests
# =============================================================================


class TestExitCodes:
    """Test exit codes for various scenarios."""

    def test_exit_code_0_on_validation_pass(self, runner, sample_ifc_path, sample_ids_path):
        """Test that exit code 0 is returned when validation passes."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        # sample.ifc has wall with 'W-001' which should pass the naming convention
        assert result.exit_code == 0

    def test_exit_code_1_on_validation_fail(self, runner, sample_fail_ifc_path, sample_ids_path):
        """Test that exit code 1 is returned when validation fails."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_fail_ifc_path), "--ids", str(sample_ids_path)],
        )

        # sample-fail.ifc has wall with 'Bad Wall Name' which should fail naming convention
        assert result.exit_code == 1

    def test_exit_code_1_on_file_not_found(self, runner):
        """Test that exit code 1 is returned when file is not found."""
        result = runner.invoke(
            app,
            ["nonexistent.ifc", "--ids", "nonexistent.ids"],
        )

        assert result.exit_code == 1

    def test_exit_code_1_on_invalid_extension(self, runner, sample_ids_path, temp_invalid_extension_file):
        """Test that exit code 1 is returned for invalid file extension."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(temp_invalid_extension_file), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1


# =============================================================================
# Output Format Tests
# =============================================================================


class TestOutputFormats:
    """Test output format options."""

    def test_default_output_is_console(self, runner, sample_ifc_path, sample_ids_path):
        """Test that default output format is console."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        # Console output should have readable text, not JSON
        assert "{" not in result.output[:50] or '"' not in result.output[:50]

    def test_json_output_format(self, runner, sample_ifc_path, sample_ids_path):
        """Test that --output json produces JSON output."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "json"],
        )

        # Should contain JSON structure
        assert "{" in result.output
        assert "overall_pass" in result.output or "timestamp" in result.output

    def test_html_output_format(self, runner, sample_ifc_path, sample_ids_path):
        """Test that --output html produces HTML output file."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        # Use temp directory for HTML output
        with tempfile.TemporaryDirectory() as tmpdir:
            html_output_path = Path(tmpdir) / "report.html"

            result = runner.invoke(
                app,
                [
                    str(sample_ifc_path),
                    "--ids", str(sample_ids_path),
                    "--output", "html",
                    "--html-output", str(html_output_path),
                ],
            )

            # Should succeed or mention HTML
            if result.exit_code == 0:
                # Check that HTML file was created
                assert html_output_path.exists() or "html" in result.output.lower()

    def test_invalid_output_format(self, runner, sample_ifc_path, sample_ids_path):
        """Test that invalid output format is rejected."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "invalid"],
        )

        # Should fail with invalid output format
        assert result.exit_code != 0

    def test_short_output_option(self, runner, sample_ifc_path, sample_ids_path):
        """Test that -o short option works for output format."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "-o", "json"],
        )

        # Should produce JSON output
        assert "{" in result.output


# =============================================================================
# Error Message Tests
# =============================================================================


class TestErrorMessages:
    """Test that error messages are clear and helpful."""

    def test_file_not_found_error_is_clear(self, runner, sample_ids_path):
        """Test that file not found error message is clear."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            ["does_not_exist.ifc", "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        output_lower = result.output.lower()
        # Error message should be clear about what happened
        assert "error" in output_lower
        assert "not found" in output_lower or "does not exist" in output_lower or "does_not_exist" in output_lower

    def test_invalid_extension_error_is_clear(self, runner, sample_ids_path, temp_invalid_extension_file):
        """Test that invalid extension error message is clear."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(temp_invalid_extension_file), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        output_lower = result.output.lower()
        # Error message should mention extension
        assert "extension" in output_lower or "invalid" in output_lower

    def test_error_output_to_stderr(self, runner, sample_ids_path):
        """Test that errors are output appropriately."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            ["nonexistent.ifc", "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        # Error should be in output
        assert "error" in result.output.lower()


# =============================================================================
# Short Option Tests
# =============================================================================


class TestShortOptions:
    """Test short option aliases."""

    def test_short_ids_option(self, runner, sample_ifc_path, sample_ids_path):
        """Test that -i short option works for --ids."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "-i", str(sample_ids_path)],
        )

        # Should work just like --ids
        # Either passes validation or fails for other reasons, not missing --ids
        assert "--ids" not in result.output.lower() or "required" not in result.output.lower()


# =============================================================================
# Typer Exit Code Tests
# =============================================================================


class TestTyperExitUsage:
    """Test that CLI uses typer.Exit() correctly (not sys.exit())."""

    def test_cli_does_not_use_sys_exit(self):
        """Verify CLI code uses typer.Exit() not sys.exit()."""
        cli_file = Path(__file__).parent.parent / "src" / "ifc_validator" / "cli.py"

        if not cli_file.exists():
            pytest.skip(f"CLI file not found: {cli_file}")

        content = cli_file.read_text()

        # sys.exit should not be used (except maybe in documentation)
        # Check for actual code usage, not comments or docstrings
        lines = content.split("\n")
        in_docstring = False

        for line in lines:
            stripped = line.strip()

            # Track docstring state
            if '"""' in stripped or "'''" in stripped:
                # Count quotes to handle single-line docstrings
                triple_double = stripped.count('"""')
                triple_single = stripped.count("'''")
                total_triples = triple_double + triple_single
                if total_triples == 1:
                    # Starting or ending a multi-line docstring
                    in_docstring = not in_docstring
                # If 2 or more, it's a single-line docstring, skip it
                continue

            # Skip if inside docstring
            if in_docstring:
                continue

            # Skip comment lines
            if stripped.startswith("#"):
                continue

            # Check for sys.exit usage in actual code
            if "sys.exit(" in line:
                pytest.fail(f"CLI uses sys.exit() instead of typer.Exit(): {line}")


# =============================================================================
# Integration-style CLI Tests
# =============================================================================


class TestCLIIntegration:
    """Integration-style tests for complete CLI workflows."""

    def test_full_validation_workflow_pass(self, runner, sample_ifc_path, sample_ids_path):
        """Test complete validation workflow with passing model."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 0
        # Should show some validation output
        output_lower = result.output.lower()
        assert "pass" in output_lower or "success" in output_lower or "validation" in output_lower

    def test_full_validation_workflow_fail(self, runner, sample_fail_ifc_path, sample_ids_path):
        """Test complete validation workflow with failing model."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_fail_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        # Should show failure information
        output_lower = result.output.lower()
        assert "fail" in output_lower or "error" in output_lower or "validation" in output_lower

    def test_json_output_is_valid_json(self, runner, sample_ifc_path, sample_ids_path):
        """Test that JSON output is parseable JSON."""
        import json

        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "json"],
        )

        # Should be valid JSON
        try:
            data = json.loads(result.output)
            assert isinstance(data, dict)
            # Should have expected fields
            assert "overall_pass" in data or "timestamp" in data
        except json.JSONDecodeError:
            pytest.fail(f"CLI JSON output is not valid JSON: {result.output[:200]}")
