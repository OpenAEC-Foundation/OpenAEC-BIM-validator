"""Unit tests for the FastAPI server in server/main.py.

Tests cover:
- Health check endpoint (/health)
- CORS configuration for viewer frontend (http://localhost:5173)
- JSON logging format validation

Usage:
    pytest test/test_server_main.py -v
    pytest test/test_server_main.py --cov=server.main --cov-report=term-missing
"""

import json
import logging
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.main import JSONFormatter, app


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# =============================================================================
# Health Endpoint Tests
# =============================================================================


class TestHealthEndpoint:
    """Test root health endpoint (/health).

    This tests the simple health endpoint at the root level that returns
    {"status": "healthy"} for basic health monitoring.
    """

    def test_health_returns_200(self, client):
        """Test that /health endpoint returns 200 status."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Test that /health endpoint returns healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_response_format(self, client):
        """Test that /health endpoint returns correct JSON format."""
        response = client.get("/health")
        data = response.json()
        assert data == {"status": "healthy"}

    def test_health_content_type_is_json(self, client):
        """Test that /health endpoint returns application/json content type."""
        response = client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")


# =============================================================================
# CORS Configuration Tests
# =============================================================================


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_allows_localhost_5173(self, client):
        """Test that CORS allows requests from localhost:5173 (viewer frontend)."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Verify the preflight request is successful
        assert response.status_code == 200

        # Verify CORS headers are present and allow the origin
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert "GET" in response.headers.get("access-control-allow-methods", "")


# =============================================================================
# JSON Logging Tests
# =============================================================================


class TestJSONLogging:
    """Test JSON logging format configuration.

    Verifies that the JSONFormatter outputs valid JSON with all required
    fields: timestamp, level, message, module, function, line.
    """

    @pytest.fixture
    def json_formatter(self):
        """Create a JSONFormatter instance for testing."""
        return JSONFormatter()

    @pytest.fixture
    def log_record(self):
        """Create a sample log record for testing."""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test_module.py",
            lineno=42,
            msg="Test log message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        return record

    def test_format_returns_valid_json(self, json_formatter, log_record):
        """Test that JSONFormatter.format() returns valid JSON."""
        output = json_formatter.format(log_record)
        # Should not raise json.JSONDecodeError
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_contains_timestamp(self, json_formatter, log_record):
        """Test that JSON output contains timestamp field."""
        output = json_formatter.format(log_record)
        parsed = json.loads(output)
        assert "timestamp" in parsed
        # Timestamp should be ISO format string
        assert isinstance(parsed["timestamp"], str)
        assert "T" in parsed["timestamp"]  # ISO format contains 'T'

    def test_json_contains_level(self, json_formatter, log_record):
        """Test that JSON output contains level field."""
        output = json_formatter.format(log_record)
        parsed = json.loads(output)
        assert "level" in parsed
        assert parsed["level"] == "INFO"

    def test_json_contains_message(self, json_formatter, log_record):
        """Test that JSON output contains message field."""
        output = json_formatter.format(log_record)
        parsed = json.loads(output)
        assert "message" in parsed
        assert parsed["message"] == "Test log message"

    def test_json_contains_module(self, json_formatter, log_record):
        """Test that JSON output contains module field."""
        output = json_formatter.format(log_record)
        parsed = json.loads(output)
        assert "module" in parsed
        assert parsed["module"] == "test_module"

    def test_json_contains_function(self, json_formatter, log_record):
        """Test that JSON output contains function field."""
        output = json_formatter.format(log_record)
        parsed = json.loads(output)
        assert "function" in parsed
        assert parsed["function"] == "test_function"

    def test_json_contains_line(self, json_formatter, log_record):
        """Test that JSON output contains line field."""
        output = json_formatter.format(log_record)
        parsed = json.loads(output)
        assert "line" in parsed
        assert parsed["line"] == 42

    def test_json_has_all_required_fields(self, json_formatter, log_record):
        """Test that JSON output contains all required fields."""
        output = json_formatter.format(log_record)
        parsed = json.loads(output)

        required_fields = ["timestamp", "level", "message", "module", "function", "line"]
        for field in required_fields:
            assert field in parsed, f"Missing required field: {field}"

    def test_format_with_different_log_levels(self, json_formatter):
        """Test that JSONFormatter works with different log levels."""
        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        for level, level_name in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="message",
                args=(),
                exc_info=None,
            )
            output = json_formatter.format(record)
            parsed = json.loads(output)
            assert parsed["level"] == level_name

    def test_format_with_message_args(self, json_formatter):
        """Test that JSONFormatter correctly formats messages with arguments."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Value is %s",
            args=("42",),
            exc_info=None,
        )
        output = json_formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "Value is 42"

    def test_timestamp_is_utc(self, json_formatter, log_record):
        """Test that timestamp is in UTC timezone."""
        output = json_formatter.format(log_record)
        parsed = json.loads(output)
        # UTC timestamps typically end with +00:00 or Z
        timestamp = parsed["timestamp"]
        assert "+00:00" in timestamp or timestamp.endswith("Z")
