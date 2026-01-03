"""Integration tests for the ifc-validate CLI end-to-end workflows.

Tests cover:
- End-to-end validation with real IFC/IDS files
- Exit codes (0 for pass, 1 for fail)
- Output format correctness (console, json, html)
- typer.Exit usage verification
- Real file validation workflows

Usage:
    pytest test/test_integration.py -v
    pytest test/test_integration.py --cov=src --cov-report=term-missing
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ifc_validator.cli import app
from ifc_validator.validator import validate, ValidationResult


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a CliRunner instance for testing."""
    return CliRunner()


@pytest.fixture
def fixtures_dir():
    """Path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_ifc_path(fixtures_dir):
    """Path to sample IFC file that passes validation."""
    return fixtures_dir / "sample.ifc"


@pytest.fixture
def sample_fail_ifc_path(fixtures_dir):
    """Path to sample IFC file that fails validation."""
    return fixtures_dir / "sample-fail.ifc"


@pytest.fixture
def sample_ids_path(fixtures_dir):
    """Path to sample IDS file."""
    return fixtures_dir / "sample.ids"


# =============================================================================
# End-to-End Validation Pass Tests
# =============================================================================


class TestEndToEndValidationPass:
    """Test end-to-end validation workflows with passing models."""

    def test_validation_pass_returns_exit_code_0(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that a passing IFC file returns exit code 0."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}. Output: {result.output}"

    def test_validation_pass_console_output_shows_success(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that console output shows success status for passing model."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 0
        output_lower = result.output.lower()
        # Should indicate pass status
        assert "pass" in output_lower or "success" in output_lower or "validation" in output_lower

    def test_validation_pass_console_output_contains_file_info(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that console output contains IFC and IDS file information."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 0
        # Should show file names
        assert "sample.ifc" in result.output
        assert "sample.ids" in result.output

    def test_validation_pass_console_output_shows_specification(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that console output shows specification details."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 0
        # Should show specification name from sample.ids
        assert "Wall" in result.output or "Naming" in result.output


# =============================================================================
# End-to-End Validation Fail Tests
# =============================================================================


class TestEndToEndValidationFail:
    """Test end-to-end validation workflows with failing models."""

    def test_validation_fail_returns_exit_code_1(
        self, runner, sample_fail_ifc_path, sample_ids_path
    ):
        """Test that a failing IFC file returns exit code 1."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_fail_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output: {result.output}"

    def test_validation_fail_console_output_shows_failure(
        self, runner, sample_fail_ifc_path, sample_ids_path
    ):
        """Test that console output shows failure status for failing model."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_fail_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        output_lower = result.output.lower()
        # Should indicate failure status
        assert "fail" in output_lower

    def test_validation_fail_console_output_shows_failed_entity(
        self, runner, sample_fail_ifc_path, sample_ids_path
    ):
        """Test that console output shows details about failed entities."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_fail_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        # Should show entity information (either wall name or type)
        output_lower = result.output.lower()
        assert "wall" in output_lower or "bad" in output_lower or "entity" in output_lower


# =============================================================================
# JSON Output Format Tests
# =============================================================================


class TestJSONOutputFormat:
    """Test JSON output format correctness."""

    def test_json_output_is_valid_json(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that --output json produces valid JSON."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "json"],
        )

        assert result.exit_code == 0
        # Should be parseable JSON
        try:
            data = json.loads(result.output)
            assert isinstance(data, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON output is not valid: {e}. Output: {result.output[:500]}")

    def test_json_output_has_required_fields(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that JSON output contains all required fields."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "json"],
        )

        data = json.loads(result.output)

        # Required fields per spec
        required_fields = [
            "timestamp",
            "ifc_file",
            "ifc_schema",
            "ifc_entity_count",
            "ids_file",
            "overall_pass",
            "specifications",
            "total_specifications",
            "passed_specifications",
            "failed_specifications",
            "pass_rate_percent",
            "validation_time_seconds",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_json_output_overall_pass_true_for_passing_model(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that JSON overall_pass is true for passing model."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "json"],
        )

        data = json.loads(result.output)
        assert data["overall_pass"] is True

    def test_json_output_overall_pass_false_for_failing_model(
        self, runner, sample_fail_ifc_path, sample_ids_path
    ):
        """Test that JSON overall_pass is false for failing model."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_fail_ifc_path), "--ids", str(sample_ids_path), "--output", "json"],
        )

        data = json.loads(result.output)
        assert data["overall_pass"] is False

    def test_json_output_specifications_structure(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that JSON specifications have correct structure."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "json"],
        )

        data = json.loads(result.output)
        assert isinstance(data["specifications"], list)
        assert len(data["specifications"]) > 0

        for spec in data["specifications"]:
            assert "name" in spec
            assert "passed" in spec
            assert "applicable_count" in spec
            assert "passed_count" in spec
            assert "failed_count" in spec
            assert "failures" in spec
            assert isinstance(spec["failures"], list)

    def test_json_output_failure_structure(
        self, runner, sample_fail_ifc_path, sample_ids_path
    ):
        """Test that JSON failures have correct structure."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_fail_ifc_path), "--ids", str(sample_ids_path), "--output", "json"],
        )

        data = json.loads(result.output)

        # Find failed specifications
        failed_specs = [s for s in data["specifications"] if not s["passed"]]
        assert len(failed_specs) > 0, "Expected at least one failed specification"

        for spec in failed_specs:
            assert len(spec["failures"]) > 0, "Failed spec should have failure details"
            for failure in spec["failures"]:
                assert "entity_id" in failure
                assert "entity_type" in failure
                # entity_name and global_id may be None

    def test_json_output_with_short_option(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that -o json works as well as --output json."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "-i", str(sample_ids_path), "-o", "json"],
        )

        data = json.loads(result.output)
        assert data["overall_pass"] is True


# =============================================================================
# HTML Output Format Tests
# =============================================================================


class TestHTMLOutputFormat:
    """Test HTML output format correctness."""

    def test_html_output_creates_file(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that --output html creates an HTML file."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            html_output = Path(tmpdir) / "report.html"

            result = runner.invoke(
                app,
                [
                    str(sample_ifc_path),
                    "--ids", str(sample_ids_path),
                    "--output", "html",
                    "--html-output", str(html_output),
                ],
            )

            assert result.exit_code == 0
            assert html_output.exists(), f"HTML file not created. Output: {result.output}"

    def test_html_output_is_valid_html(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that HTML output is valid HTML document."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            html_output = Path(tmpdir) / "report.html"

            result = runner.invoke(
                app,
                [
                    str(sample_ifc_path),
                    "--ids", str(sample_ids_path),
                    "--output", "html",
                    "--html-output", str(html_output),
                ],
            )

            assert result.exit_code == 0
            assert html_output.exists()

            content = html_output.read_text(encoding="utf-8")
            # Check for valid HTML structure
            assert "<!DOCTYPE html>" in content
            assert "<html" in content
            assert "</html>" in content
            assert "<head>" in content
            assert "<body>" in content

    def test_html_output_contains_validation_data(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that HTML output contains validation data."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            html_output = Path(tmpdir) / "report.html"

            result = runner.invoke(
                app,
                [
                    str(sample_ifc_path),
                    "--ids", str(sample_ids_path),
                    "--output", "html",
                    "--html-output", str(html_output),
                ],
            )

            assert result.exit_code == 0
            content = html_output.read_text(encoding="utf-8")

            # Should contain file names
            assert "sample.ifc" in content
            # Should show pass/fail status
            assert "PASS" in content or "pass" in content.lower()

    def test_html_output_failing_model(
        self, runner, sample_fail_ifc_path, sample_ids_path
    ):
        """Test HTML output for failing model."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            html_output = Path(tmpdir) / "report.html"

            result = runner.invoke(
                app,
                [
                    str(sample_fail_ifc_path),
                    "--ids", str(sample_ids_path),
                    "--output", "html",
                    "--html-output", str(html_output),
                ],
            )

            assert result.exit_code == 1
            assert html_output.exists()

            content = html_output.read_text(encoding="utf-8")
            # Should show fail status
            assert "FAIL" in content or "fail" in content.lower()

    def test_html_output_default_filename(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test HTML output uses default filename when --html-output not specified."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        # Change to temp directory for this test
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                result = runner.invoke(
                    app,
                    [
                        str(sample_ifc_path),
                        "--ids", str(sample_ids_path),
                        "--output", "html",
                    ],
                )

                assert result.exit_code == 0
                # Default filename should be <ifc_stem>_report.html
                expected_file = Path(tmpdir) / "sample_report.html"
                assert expected_file.exists(), f"Expected {expected_file} to be created. Output: {result.output}"
            finally:
                os.chdir(original_cwd)


# =============================================================================
# Console Output Format Tests
# =============================================================================


class TestConsoleOutputFormat:
    """Test console (default) output format."""

    def test_console_is_default_format(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that console is the default output format."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        # Default should be console, not JSON (which would start with { )
        assert result.exit_code == 0
        # Console output has Rich formatting, not raw JSON
        assert not result.output.strip().startswith("{")

    def test_console_output_has_substantial_content(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that console output has substantial formatted content."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 0
        # Should have substantial output (tables, panels, etc.)
        assert len(result.output) > 100

    def test_console_output_explicit_format(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that --output console explicitly sets console format."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "console"],
        )

        assert result.exit_code == 0
        # Should be console format, not JSON
        assert not result.output.strip().startswith("{")


# =============================================================================
# Typer Exit Code Tests
# =============================================================================


class TestTyperExitUsage:
    """Test that CLI uses typer.Exit() correctly (not sys.exit())."""

    def test_cli_source_uses_typer_exit(self):
        """Verify CLI code uses typer.Exit() not sys.exit()."""
        cli_file = Path(__file__).parent.parent / "src" / "ifc_validator" / "cli.py"

        if not cli_file.exists():
            pytest.skip(f"CLI file not found: {cli_file}")

        content = cli_file.read_text()

        # Should use typer.Exit
        assert "typer.Exit" in content, "CLI must use typer.Exit() for exit codes"

        # Should NOT use sys.exit in actual code (excluding imports/comments/docstrings)
        lines = content.split("\n")
        in_docstring = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track multi-line docstrings
            if '"""' in stripped or "'''" in stripped:
                triple_count = stripped.count('"""') + stripped.count("'''")
                if triple_count == 1:
                    in_docstring = not in_docstring
                continue

            # Skip if inside docstring
            if in_docstring:
                continue

            # Skip comment lines
            if stripped.startswith("#"):
                continue

            # Skip import lines
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue

            # Check for sys.exit usage in actual code
            if "sys.exit(" in line:
                pytest.fail(f"Line {i}: CLI uses sys.exit() instead of typer.Exit(): {line.strip()}")

    def test_exit_code_propagates_correctly_on_pass(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test exit code 0 is correctly propagated on validation pass."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path)],
        )

        # Typer.Exit(code=0) should result in exit_code 0
        assert result.exit_code == 0

    def test_exit_code_propagates_correctly_on_fail(
        self, runner, sample_fail_ifc_path, sample_ids_path
    ):
        """Test exit code 1 is correctly propagated on validation fail."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_fail_ifc_path), "--ids", str(sample_ids_path)],
        )

        # Typer.Exit(code=1) should result in exit_code 1
        assert result.exit_code == 1

    def test_exit_code_propagates_on_error(self, runner, sample_ids_path):
        """Test exit code 1 is correctly propagated on file not found error."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            ["nonexistent_file.ifc", "--ids", str(sample_ids_path)],
        )

        # Typer.Exit(code=1) should result in exit_code 1
        assert result.exit_code == 1


# =============================================================================
# Error Scenario Tests
# =============================================================================


class TestErrorScenarios:
    """Test error handling scenarios in end-to-end flows."""

    def test_missing_ifc_file_returns_exit_1(self, runner, sample_ids_path):
        """Test that missing IFC file returns exit code 1."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            ["does_not_exist.ifc", "--ids", str(sample_ids_path)],
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_missing_ids_file_returns_exit_1(self, runner, sample_ifc_path):
        """Test that missing IDS file returns exit code 1."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", "does_not_exist.ids"],
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_invalid_ifc_extension_returns_exit_1(
        self, runner, sample_ids_path
    ):
        """Test that invalid IFC extension returns exit code 1."""
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Not an IFC file")
            temp_path = f.name

        try:
            result = runner.invoke(
                app,
                [temp_path, "--ids", str(sample_ids_path)],
            )

            assert result.exit_code == 1
            output_lower = result.output.lower()
            assert "error" in output_lower
            assert "extension" in output_lower or "invalid" in output_lower
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_invalid_ids_extension_returns_exit_1(
        self, runner, sample_ifc_path
    ):
        """Test that invalid IDS extension returns exit code 1."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"<xml>Not an IDS file</xml>")
            temp_path = f.name

        try:
            result = runner.invoke(
                app,
                [str(sample_ifc_path), "--ids", temp_path],
            )

            assert result.exit_code == 1
            output_lower = result.output.lower()
            assert "error" in output_lower
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_invalid_output_format_returns_exit_non_zero(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that invalid output format is rejected."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "--ids", str(sample_ids_path), "--output", "invalid"],
        )

        # Typer should reject invalid enum value
        assert result.exit_code != 0


# =============================================================================
# Validator Function Integration Tests
# =============================================================================


class TestValidatorIntegration:
    """Test validator module integration with real files."""

    def test_validate_function_returns_validation_result(
        self, sample_ifc_path, sample_ids_path
    ):
        """Test that validate function returns ValidationResult."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        assert isinstance(result, ValidationResult)
        assert result.ifc_file == sample_ifc_path.name
        assert result.ids_file == sample_ids_path.name

    def test_validate_function_passing_model(
        self, sample_ifc_path, sample_ids_path
    ):
        """Test validate function with passing model."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        assert result.overall_pass is True
        assert result.passed_specifications > 0
        assert result.failed_specifications == 0

    def test_validate_function_failing_model(
        self, sample_fail_ifc_path, sample_ids_path
    ):
        """Test validate function with failing model."""
        if not sample_fail_ifc_path.exists():
            pytest.skip(f"Sample fail IFC file not found: {sample_fail_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_fail_ifc_path, sample_ids_path)

        assert result.overall_pass is False
        assert result.failed_specifications > 0

    def test_validate_function_extracts_ifc_schema(
        self, sample_ifc_path, sample_ids_path
    ):
        """Test that validate function extracts IFC schema version."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        # sample.ifc uses IFC4 schema
        assert result.ifc_schema is not None
        assert "IFC" in result.ifc_schema.upper()

    def test_validate_function_includes_timing(
        self, sample_ifc_path, sample_ids_path
    ):
        """Test that validate function includes timing information."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = validate(sample_ifc_path, sample_ids_path)

        assert result.validation_time_seconds >= 0
        assert isinstance(result.validation_time_seconds, float)


# =============================================================================
# CLI Options Tests
# =============================================================================


class TestCLIOptions:
    """Test CLI option handling."""

    def test_help_flag_shows_usage(self, runner):
        """Test that --help shows usage information."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "--ids" in result.output
        assert "--output" in result.output

    def test_version_flag_shows_version(self, runner):
        """Test that --version shows version information."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_short_ids_option_works(
        self, runner, sample_ifc_path, sample_ids_path
    ):
        """Test that -i works as alias for --ids."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")
        if not sample_ids_path.exists():
            pytest.skip(f"Sample IDS file not found: {sample_ids_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path), "-i", str(sample_ids_path)],
        )

        assert result.exit_code == 0

    def test_missing_required_ids_option(self, runner, sample_ifc_path):
        """Test that missing --ids option results in error."""
        if not sample_ifc_path.exists():
            pytest.skip(f"Sample IFC file not found: {sample_ifc_path}")

        result = runner.invoke(
            app,
            [str(sample_ifc_path)],
        )

        # Missing required option should fail
        assert result.exit_code != 0
