# Testing Guide - IFC Validator

This document describes the testing infrastructure, conventions, and how to contribute tests.

---

## Quick Start

```bash
# 1. Install dev dependencies
pip install -e ".[dev]"

# 2. Run all tests with coverage
pytest

# 3. View coverage report
open htmlcov/index.html   # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

---

## Test Structure

```
test/
├── conftest.py              ← Shared fixtures and pytest configuration
├── fixtures/                ← Sample IFC and IDS files
│   ├── sample.ifc          ← Valid IFC file (passes validation)
│   ├── sample-fail.ifc     ← Invalid IFC file (fails validation)
│   └── sample.ids          ← IDS specification file
├── test_validator.py        ← Validator module tests
├── test_ifc_parser.py       ← IFC parser tests
├── test_ifc_processor.py    ← IFC processor tests
├── test_ids_validator.py    ← IDS validation tests
├── test_formatters.py       ← Output formatter tests (console, HTML, JSON)
├── test_cli.py              ← CLI command tests
├── test_server_main.py      ← FastAPI endpoint tests
├── test_integration.py      ← Integration tests
└── test_module_imports.py   ← Module import verification
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest test/test_validator.py

# Run specific test function
pytest test/test_validator.py::test_validate_file_exists

# Run tests matching pattern
pytest -k "validation"

# Run tests with verbose output
pytest -v

# Run tests without coverage (faster)
pytest --no-cov
```

### Coverage Reports

```bash
# Terminal report with missing lines
pytest --cov-report=term-missing

# Generate HTML report
pytest --cov-report=html
# Then open htmlcov/index.html

# Generate XML report (for CI)
pytest --cov-report=xml:coverage.xml
```

### Test Selection

```bash
# Run only unit tests (exclude integration)
pytest --ignore=test/test_integration.py

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run failed tests from last run
pytest --lf

# Run tests that were modified
pytest --ff
```

---

## Coverage Requirements

### Minimum Threshold: 80%

The test suite enforces a **minimum 80% code coverage**. Tests will fail if coverage drops below this threshold.

Configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--cov-fail-under=80"

[tool.coverage.report]
fail_under = 80
```

### Coverage Exclusions

The following patterns are excluded from coverage:

- `pragma: no cover` comments
- `def __repr__` methods
- `raise NotImplementedError`
- `if TYPE_CHECKING:` blocks
- `if __name__ == "__main__":` blocks
- Test files and `__pycache__` directories

---

## Test Fixtures

### Using Fixtures

Fixtures are defined in `test/conftest.py` and individual test files:

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_ifc_path():
    """Path to sample IFC file that passes validation."""
    return Path(__file__).parent / "fixtures" / "sample.ifc"

@pytest.fixture
def sample_ids_path():
    """Path to sample IDS file."""
    return Path(__file__).parent / "fixtures" / "sample.ids"

def test_validation_passes(sample_ifc_path, sample_ids_path):
    """Test that valid IFC passes validation."""
    result = validate(sample_ifc_path, sample_ids_path)
    assert result.passed is True
```

### Available Fixture Files

| File | Description |
|------|-------------|
| `fixtures/sample.ifc` | Valid IFC file that passes validation |
| `fixtures/sample-fail.ifc` | Invalid IFC file that fails validation |
| `fixtures/sample.ids` | Sample IDS specification |

### Creating Temporary Files

Use `tempfile` for temporary test files:

```python
import tempfile
from pathlib import Path

@pytest.fixture
def temp_ifc_file():
    """Create a temporary IFC file."""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        f.write(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;")
        temp_path = f.name
    yield Path(temp_path)
    # Cleanup after test
    if os.path.exists(temp_path):
        os.unlink(temp_path)
```

---

## Adding New Tests

### 1. Naming Conventions

- **Files**: `test_<module_name>.py`
- **Classes**: `Test<FeatureName>` (optional, for grouping)
- **Functions**: `test_<what_is_being_tested>`

```python
# Good names
def test_validate_returns_true_for_valid_ifc():
def test_parser_raises_error_on_invalid_file():
def test_memory_check_with_insufficient_memory():

# Bad names
def test_1():
def testValidation():
def check_parser():
```

### 2. Test Structure (AAA Pattern)

Follow the Arrange-Act-Assert pattern:

```python
def test_validation_with_invalid_extension(temp_invalid_file):
    """Test that validation fails with invalid file extension."""
    # Arrange
    invalid_path = temp_invalid_file

    # Act
    with pytest.raises(ValueError) as exc_info:
        validate_ifc_extension(invalid_path)

    # Assert
    assert "Invalid IFC extension" in str(exc_info.value)
```

### 3. Testing Edge Cases

Always test error conditions:

```python
def test_validate_file_not_found():
    """Test error handling for missing files."""
    with pytest.raises(FileNotFoundError):
        validate_file_exists(Path("/nonexistent/file.ifc"))

def test_validate_with_none_input():
    """Test error handling for None input."""
    with pytest.raises(TypeError):
        validate(None, None)

def test_validate_empty_file(temp_empty_ifc):
    """Test error handling for empty files."""
    with pytest.raises(ValueError):
        validate(temp_empty_ifc, sample_ids_path)
```

### 4. Using Parametrize

Test multiple inputs efficiently:

```python
@pytest.mark.parametrize("extension,expected", [
    (".ifc", True),
    (".IFC", True),
    (".ifczip", True),
    (".txt", False),
    (".ifc.bak", False),
])
def test_ifc_extension_validation(extension, expected):
    """Test IFC extension validation with various extensions."""
    result = is_valid_ifc_extension(extension)
    assert result == expected
```

### 5. Mocking External Dependencies

Use `unittest.mock` for external dependencies:

```python
from unittest.mock import patch, MagicMock

def test_validation_with_ifcopenshell_error():
    """Test handling of ifcopenshell errors."""
    with patch("ifcopenshell.open") as mock_open:
        mock_open.side_effect = RuntimeError("Parse error")

        with pytest.raises(RuntimeError):
            load_ifc_model(Path("test.ifc"))

@patch("psutil.virtual_memory")
def test_memory_check_insufficient(mock_memory):
    """Test memory check with insufficient memory."""
    mock_memory.return_value = MagicMock(available=100)

    result = check_memory_available(file_size=1000)
    assert result is False
```

### 6. Testing FastAPI Endpoints

Use `TestClient` for API tests:

```python
from fastapi.testclient import TestClient
from server.main import app

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

def test_health_endpoint(client):
    """Test health check returns 200."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_upload_invalid_file(client):
    """Test upload rejects invalid files."""
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", b"not an ifc", "text/plain")}
    )
    assert response.status_code == 400
```

---

## CI/CD Integration

### GitHub Actions Workflow

Tests run automatically on:
- Push to `main`, `master`, or `develop`
- Pull requests to these branches
- Manual trigger via `workflow_dispatch`

The workflow (`.github/workflows/test.yml`):
1. Runs tests on Python 3.9, 3.10, 3.11, and 3.12
2. Enforces 80% coverage threshold
3. Posts coverage report as PR comment
4. Runs Black and Ruff linting
5. Acts as merge gate (all checks must pass)

### Coverage Artifacts

Coverage reports are uploaded as GitHub Actions artifacts:
- `coverage.xml` - XML report for tools
- `htmlcov/` - HTML report for viewing

---

## Best Practices

### DO

- Write descriptive test names that explain the scenario
- Test both success and failure paths
- Use fixtures for reusable test data
- Keep tests fast and isolated
- Use `pytest.mark.parametrize` for multiple input variations
- Add docstrings explaining what each test verifies
- Mock external dependencies (filesystem, network)

### DON'T

- Don't test third-party libraries (ifcopenshell, ifctester)
- Don't write integration tests when unit tests suffice
- Don't commit large binary IFC files
- Don't hardcode file paths
- Don't skip error handling tests
- Don't leave `print()` statements in tests

---

## Troubleshooting

### Common Issues

**Tests not discovered:**
```bash
# Check test collection
pytest --collect-only
```

**Import errors:**
```bash
# Ensure package is installed
pip install -e ".[dev]"
```

**Coverage too low:**
```bash
# Check what's missing
pytest --cov-report=term-missing
```

**Tests timing out:**
```bash
# Increase timeout
pytest --timeout=60
```

### Worktree Isolation

The `conftest.py` ensures tests use the local `src/` directory, preventing cross-contamination from other worktrees. This is automatically handled.

---

## Useful Commands Reference

| Command | Description |
|---------|-------------|
| `pytest` | Run all tests with coverage |
| `pytest -v` | Verbose output |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Run last failed tests |
| `pytest -k "pattern"` | Run tests matching pattern |
| `pytest --no-cov` | Skip coverage (faster) |
| `pytest --cov-report=html` | Generate HTML report |
| `black .` | Format code |
| `ruff check .` | Lint code |
| `ruff check . --fix` | Auto-fix lint issues |

---

## Links

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

---

© 2025 3BM Bouwkunde - Ingenieurs van oplossingen
