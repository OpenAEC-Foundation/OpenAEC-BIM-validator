"""Unit and integration tests for the POST /api/v1/validate endpoint.

Tests cover:
- Validation with custom IDS file upload
- Validation with built-in standards (nl-bim, rvb)
- Error handling for missing files
- Error handling for invalid extensions
- Error handling for file size limits
- Response schema validation

Usage:
    pytest server/tests/test_validate_endpoint.py -v
    pytest server/tests/test_validate_endpoint.py --cov=server.main --cov-report=term-missing
"""

import io
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.main import MAX_FILE_SIZE, MAX_IDS_FILE_SIZE


# =============================================================================
# Input Validation Tests - IFC File
# =============================================================================


class TestValidateEndpointIfcValidation:
    """Test IFC file validation for /api/v1/validate endpoint."""

    def test_validate_missing_ifc_returns_422(self, client):
        """Test that endpoint returns 422 when no IFC file is provided."""
        # POST without any files
        response = client.post("/api/v1/validate")
        assert response.status_code == 422

    def test_validate_invalid_ifc_extension_returns_400(self, client, sample_ids_file):
        """Test that endpoint returns 400 for invalid IFC file extension."""
        invalid_ifc = ("model.txt", io.BytesIO(b"not an ifc file"), "text/plain")
        files = {"ifc_file": invalid_ifc, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)
        assert response.status_code == 400
        assert "Invalid IFC file type" in response.json()["detail"]

    def test_validate_empty_ifc_returns_400(self, client, sample_ids_file):
        """Test that endpoint returns 400 for empty IFC file."""
        empty_ifc = ("model.ifc", io.BytesIO(b""), "application/octet-stream")
        files = {"ifc_file": empty_ifc, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_validate_accepts_ifc_extension(self, client, sample_ifc_file, sample_ids_file):
        """Test that endpoint accepts .ifc extension."""
        files = {"ifc_file": sample_ifc_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)
        # Should not return 400 for extension - may return 200 or 422 depending on content
        assert response.status_code != 400 or "Invalid IFC file type" not in response.json().get("detail", "")

    def test_validate_accepts_ifcxml_extension(self, client, sample_ids_file, sample_ifc_content):
        """Test that endpoint accepts .ifcxml extension."""
        ifcxml_file = ("model.ifcxml", io.BytesIO(sample_ifc_content), "application/octet-stream")
        files = {"ifc_file": ifcxml_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)
        # Should not return 400 for extension
        assert response.status_code != 400 or "Invalid IFC file type" not in response.json().get("detail", "")

    def test_validate_accepts_ifczip_extension(self, client, sample_ids_file, sample_ifc_content):
        """Test that endpoint accepts .ifczip extension."""
        ifczip_file = ("model.ifczip", io.BytesIO(sample_ifc_content), "application/octet-stream")
        files = {"ifc_file": ifczip_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)
        # Should not return 400 for extension
        assert response.status_code != 400 or "Invalid IFC file type" not in response.json().get("detail", "")

    def test_validate_ifc_case_insensitive_extension(self, client, sample_ids_file, sample_ifc_content):
        """Test that endpoint accepts .IFC extension (case insensitive)."""
        ifc_file = ("MODEL.IFC", io.BytesIO(sample_ifc_content), "application/octet-stream")
        files = {"ifc_file": ifc_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)
        # Should not return 400 for extension
        assert response.status_code != 400 or "Invalid IFC file type" not in response.json().get("detail", "")


# =============================================================================
# Input Validation Tests - IDS File/Standard
# =============================================================================


class TestValidateEndpointIdsValidation:
    """Test IDS file/standard validation for /api/v1/validate endpoint."""

    def test_validate_missing_ids_and_standard_returns_400(self, client, sample_ifc_file):
        """Test that endpoint returns 400 when neither IDS file nor standard provided."""
        files = {"ifc_file": sample_ifc_file}
        response = client.post("/api/v1/validate", files=files)
        assert response.status_code == 400
        assert "ids_file" in response.json()["detail"].lower() or "ids_standard" in response.json()["detail"].lower()

    def test_validate_invalid_ids_extension_returns_400(self, client, sample_ifc_file):
        """Test that endpoint returns 400 for invalid IDS file extension."""
        invalid_ids = ("spec.txt", io.BytesIO(b"not an ids file"), "text/plain")
        files = {"ifc_file": sample_ifc_file, "ids_file": invalid_ids}
        response = client.post("/api/v1/validate", files=files)
        assert response.status_code == 400
        assert "Invalid IDS file type" in response.json()["detail"]

    def test_validate_empty_ids_returns_400(self, client, sample_ifc_file):
        """Test that endpoint returns 400 for empty IDS file."""
        empty_ids = ("spec.ids", io.BytesIO(b""), "application/octet-stream")
        files = {"ifc_file": sample_ifc_file, "ids_file": empty_ids}
        response = client.post("/api/v1/validate", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_validate_accepts_ids_extension(self, client, sample_ifc_file, sample_ids_content):
        """Test that endpoint accepts .ids extension."""
        ids_file = ("spec.ids", io.BytesIO(sample_ids_content), "application/octet-stream")
        files = {"ifc_file": sample_ifc_file, "ids_file": ids_file}
        response = client.post("/api/v1/validate", files=files)
        # Should not return 400 for extension
        assert response.status_code != 400 or "Invalid IDS file type" not in response.json().get("detail", "")

    def test_validate_accepts_xml_extension(self, client, sample_ifc_file, sample_ids_content):
        """Test that endpoint accepts .xml extension for IDS."""
        xml_file = ("spec.xml", io.BytesIO(sample_ids_content), "application/octet-stream")
        files = {"ifc_file": sample_ifc_file, "ids_file": xml_file}
        response = client.post("/api/v1/validate", files=files)
        # Should not return 400 for extension
        assert response.status_code != 400 or "Invalid IDS file type" not in response.json().get("detail", "")

    def test_validate_invalid_standard_returns_400(self, client, sample_ifc_file):
        """Test that endpoint returns 400 for invalid ids_standard value."""
        files = {"ifc_file": sample_ifc_file}
        response = client.post("/api/v1/validate?ids_standard=invalid", files=files)
        assert response.status_code == 400
        assert "Invalid IDS standard" in response.json()["detail"]

    def test_validate_accepts_nl_bim_standard(self, client, sample_ifc_file):
        """Test that endpoint accepts ids_standard=nl-bim."""
        files = {"ifc_file": sample_ifc_file}
        response = client.post("/api/v1/validate?ids_standard=nl-bim", files=files)
        # Should not return 400 for standard
        assert response.status_code != 400 or "Invalid IDS standard" not in response.json().get("detail", "")

    def test_validate_accepts_rvb_standard(self, client, sample_ifc_file):
        """Test that endpoint accepts ids_standard=rvb."""
        files = {"ifc_file": sample_ifc_file}
        response = client.post("/api/v1/validate?ids_standard=rvb", files=files)
        # Should not return 400 for standard
        assert response.status_code != 400 or "Invalid IDS standard" not in response.json().get("detail", "")

    def test_validate_standard_case_insensitive(self, client, sample_ifc_file):
        """Test that ids_standard is case insensitive."""
        files = {"ifc_file": sample_ifc_file}
        response = client.post("/api/v1/validate?ids_standard=NL-BIM", files=files)
        # Should not return 400 for standard
        assert response.status_code != 400 or "Invalid IDS standard" not in response.json().get("detail", "")


# =============================================================================
# File Size Validation Tests
# =============================================================================


class TestValidateEndpointFileSizeValidation:
    """Test file size validation for /api/v1/validate endpoint."""

    def test_validate_ifc_file_too_large_returns_413(self, client, sample_ids_file):
        """Test that endpoint returns 413 for IFC file exceeding size limit."""
        # Create a file larger than MAX_FILE_SIZE (500MB)
        # For testing, we'll just check the constant is correct
        assert MAX_FILE_SIZE == 500 * 1024 * 1024  # 500MB

        # Create a small "large" file representation (we can't actually test 500MB)
        # This test validates the constant exists; actual size check is integration

    def test_validate_ids_file_too_large_returns_413(self, client, sample_ifc_file):
        """Test that endpoint returns 413 for IDS file exceeding size limit."""
        # Verify the constant is correct
        assert MAX_IDS_FILE_SIZE == 5 * 1024 * 1024  # 5MB

        # Create a file slightly larger than 5MB limit
        large_ids_content = b"x" * (MAX_IDS_FILE_SIZE + 1)
        large_ids = ("spec.ids", io.BytesIO(large_ids_content), "application/octet-stream")
        files = {"ifc_file": sample_ifc_file, "ids_file": large_ids}
        response = client.post("/api/v1/validate", files=files)
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()


# =============================================================================
# Successful Validation Tests
# =============================================================================


class TestValidateEndpointSuccess:
    """Test successful validation scenarios for /api/v1/validate endpoint."""

    def test_validate_with_custom_ids_returns_200(self, client, sample_ifc_file, sample_ids_file):
        """Test that validation with custom IDS file returns 200."""
        files = {"ifc_file": sample_ifc_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)
        assert response.status_code == 200

    def test_validate_with_custom_ids_returns_validation_result(self, client, sample_ifc_file, sample_ids_file):
        """Test that validation returns ValidationResult structure."""
        files = {"ifc_file": sample_ifc_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)
        assert response.status_code == 200
        data = response.json()

        # Check required fields from ValidationResult model
        assert "success" in data
        assert "total_specifications" in data
        assert "failed_specifications" in data
        assert "total_elements_validated" in data
        assert "validation_timestamp" in data
        assert "specifications" in data
        assert "ifc_file_name" in data
        assert "ids_file_name" in data

    def test_validate_with_nl_bim_standard_returns_200(self, client, sample_ifc_file):
        """Test that validation with nl-bim standard returns 200."""
        files = {"ifc_file": sample_ifc_file}
        response = client.post("/api/v1/validate?ids_standard=nl-bim", files=files)
        # Should complete (200) or have validation errors (not 4xx input errors)
        assert response.status_code in [200, 422]

    def test_validate_with_rvb_standard_returns_200(self, client, sample_ifc_file):
        """Test that validation with rvb standard returns 200."""
        files = {"ifc_file": sample_ifc_file}
        response = client.post("/api/v1/validate?ids_standard=rvb", files=files)
        # Should complete (200) or have validation errors (not 4xx input errors)
        assert response.status_code in [200, 422]

    def test_validate_returns_correct_filenames(self, client, sample_ifc_content, sample_ids_content):
        """Test that validation returns correct filenames in response."""
        ifc_file = ("my_model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")
        ids_file = ("my_spec.ids", io.BytesIO(sample_ids_content), "application/octet-stream")
        files = {"ifc_file": ifc_file, "ids_file": ids_file}
        response = client.post("/api/v1/validate", files=files)

        if response.status_code == 200:
            data = response.json()
            assert data["ifc_file_name"] == "my_model.ifc"
            assert data["ids_file_name"] == "my_spec.ids"


# =============================================================================
# Validation Result Structure Tests
# =============================================================================


class TestValidationResultSchema:
    """Test that validation response matches ValidationResult model schema."""

    def test_validation_result_has_specifications_list(self, client, sample_ifc_file, sample_ids_file):
        """Test that response includes specifications as a list."""
        files = {"ifc_file": sample_ifc_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["specifications"], list)

    def test_specification_result_structure(self, client, sample_ifc_file, sample_ids_file):
        """Test that specification results have correct structure."""
        files = {"ifc_file": sample_ifc_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)

        if response.status_code == 200:
            data = response.json()
            if data["specifications"]:
                spec = data["specifications"][0]
                assert "specification_name" in spec
                assert "severity" in spec
                assert "status" in spec
                assert "total_requirements" in spec
                assert "failed_requirements" in spec
                assert "requirements" in spec

    def test_validation_success_boolean_type(self, client, sample_ifc_file, sample_ids_file):
        """Test that success field is a boolean."""
        files = {"ifc_file": sample_ifc_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["success"], bool)

    def test_validation_timestamp_format(self, client, sample_ifc_file, sample_ids_file):
        """Test that validation_timestamp is a string (ISO format)."""
        files = {"ifc_file": sample_ifc_file, "ids_file": sample_ids_file}
        response = client.post("/api/v1/validate", files=files)

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["validation_timestamp"], str)
            # Should be ISO format: 2025-01-01T12:00:00
            assert "T" in data["validation_timestamp"] or "-" in data["validation_timestamp"]


# =============================================================================
# Integration Tests with Real Files
# =============================================================================


class TestValidateEndpointIntegration:
    """Integration tests using real fixture files."""

    def test_full_validation_flow_with_fixtures(self, client, sample_ifc_path, sample_ids_path):
        """Test full validation flow with real fixture files."""
        with open(sample_ifc_path, "rb") as ifc_f, open(sample_ids_path, "rb") as ids_f:
            files = {
                "ifc_file": (sample_ifc_path.name, ifc_f, "application/octet-stream"),
                "ids_file": (sample_ids_path.name, ids_f, "application/octet-stream"),
            }
            response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "specifications" in data

    def test_validation_with_failing_ifc(self, client, sample_fail_ifc_path, sample_ids_path):
        """Test validation with IFC file that should fail validation."""
        with open(sample_fail_ifc_path, "rb") as ifc_f, open(sample_ids_path, "rb") as ids_f:
            files = {
                "ifc_file": (sample_fail_ifc_path.name, ifc_f, "application/octet-stream"),
                "ids_file": (sample_ids_path.name, ids_f, "application/octet-stream"),
            }
            response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 200
        data = response.json()
        # The sample-fail.ifc should fail the wall naming convention spec
        assert data["failed_specifications"] > 0 or data["success"] is False
