"""Unit tests for the FastAPI server endpoints in server/main.py.

Tests cover:
- Root endpoint (/)
- Health check endpoint (/api/health)
- File upload endpoint (/api/upload)
- File status endpoint (/api/status/{file_id})
- List files endpoint (/api/files)
- Delete file endpoints (/api/files/{file_id}, /api/files)
- Process endpoint (/api/process/{file_id})
- Download endpoint (/api/download/{file_id})
- Capabilities endpoint (/api/capabilities)

Usage:
    pytest test/test_server_main.py -v
    pytest test/test_server_main.py --cov=server.main --cov-report=term-missing
"""

import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.ifc_processor import ProcessingResult
from server.main import (
    MAX_FILE_SIZE,
    PROCESSED_DIR,
    UPLOAD_DIR,
    app,
    uploaded_files,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_ifc_content():
    """Sample valid IFC file content for testing."""
    return b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;"


@pytest.fixture
def uploaded_file_id(client, sample_ifc_content):
    """Upload a file and return its file_id for testing."""
    files = {"ifc_file": ("test_model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 200
    return response.json()["file_id"]


@pytest.fixture(autouse=True)
def cleanup_uploaded_files():
    """Clean up uploaded_files tracking dict before and after each test."""
    # Clear before test
    uploaded_files.clear()
    yield
    # Clear after test
    uploaded_files.clear()


# =============================================================================
# Root Endpoint Tests
# =============================================================================


class TestRootEndpoint:
    """Test root endpoint (/)."""

    def test_root_returns_200(self, client):
        """Test that root endpoint returns 200 status."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_healthy_status(self, client):
        """Test that root endpoint returns healthy status."""
        response = client.get("/")
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_returns_service_info(self, client):
        """Test that root endpoint returns service information."""
        response = client.get("/")
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_root_returns_endpoints_info(self, client):
        """Test that root endpoint returns available endpoints."""
        response = client.get("/")
        data = response.json()
        assert "endpoints" in data
        assert "upload" in data["endpoints"]
        assert "status" in data["endpoints"]
        assert "docs" in data["endpoints"]


# =============================================================================
# Health Endpoint Tests (root /health)
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
# Health Check Endpoint Tests (/api/health)
# =============================================================================


class TestHealthCheckEndpoint:
    """Test health check endpoint (/api/health)."""

    def test_api_health_returns_200(self, client):
        """Test that /api/health endpoint returns 200 status."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_api_health_returns_ok_status(self, client):
        """Test that /api/health endpoint returns ok status."""
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_upload_dir_info(self, client):
        """Test that health endpoint returns upload directory info."""
        response = client.get("/api/health")
        data = response.json()
        assert "upload_dir" in data
        assert "upload_dir_exists" in data
        assert isinstance(data["upload_dir_exists"], bool)

    def test_health_returns_processed_dir_info(self, client):
        """Test that health endpoint returns processed directory info."""
        response = client.get("/api/health")
        data = response.json()
        assert "processed_dir" in data

    def test_health_returns_files_tracked_count(self, client):
        """Test that health endpoint returns tracked files count."""
        response = client.get("/api/health")
        data = response.json()
        assert "files_tracked" in data
        assert data["files_tracked"] == 0  # After cleanup fixture

    def test_health_returns_processor_capabilities(self, client):
        """Test that health endpoint returns processor capabilities."""
        response = client.get("/api/health")
        data = response.json()
        assert "processor_capabilities" in data


# =============================================================================
# Upload Endpoint Tests
# =============================================================================


class TestUploadEndpoint:
    """Test file upload endpoint (/api/upload)."""

    def test_upload_valid_ifc_returns_200(self, client, sample_ifc_content):
        """Test that uploading a valid IFC file returns 200."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200

    def test_upload_returns_success_true(self, client, sample_ifc_content):
        """Test that successful upload returns success=True."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        data = response.json()
        assert data["success"] is True

    def test_upload_returns_file_id(self, client, sample_ifc_content):
        """Test that successful upload returns a file_id."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        data = response.json()
        assert "file_id" in data
        assert len(data["file_id"]) == 36  # UUID format

    def test_upload_returns_filename(self, client, sample_ifc_content):
        """Test that successful upload returns original filename."""
        files = {"ifc_file": ("test_model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        data = response.json()
        assert data["filename"] == "test_model.ifc"

    def test_upload_returns_file_size(self, client, sample_ifc_content):
        """Test that successful upload returns file size."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        data = response.json()
        assert data["file_size"] == len(sample_ifc_content)
        assert "file_size_mb" in data

    def test_upload_returns_upload_time(self, client, sample_ifc_content):
        """Test that successful upload returns upload time."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        data = response.json()
        assert "upload_time_ms" in data
        assert data["upload_time_ms"] >= 0

    def test_upload_returns_status_uploaded(self, client, sample_ifc_content):
        """Test that successful upload returns status=uploaded."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        data = response.json()
        assert data["status"] == "uploaded"

    def test_upload_returns_next_step(self, client, sample_ifc_content):
        """Test that successful upload returns next step hint."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        data = response.json()
        assert "next_step" in data
        assert "/api/process/" in data["next_step"]

    def test_upload_invalid_extension_returns_400(self, client):
        """Test that uploading non-IFC file returns 400."""
        files = {"ifc_file": ("model.txt", io.BytesIO(b"not an ifc file"), "text/plain")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_empty_file_returns_400(self, client):
        """Test that uploading empty file returns 400."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(b""), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]

    def test_upload_case_insensitive_extension(self, client, sample_ifc_content):
        """Test that upload accepts .IFC extension (case insensitive)."""
        files = {"ifc_file": ("MODEL.IFC", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200

    def test_upload_tracks_file(self, client, sample_ifc_content):
        """Test that uploaded file is tracked in uploaded_files."""
        files = {"ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        file_id = response.json()["file_id"]
        assert file_id in uploaded_files
        assert uploaded_files[file_id]["original_filename"] == "model.ifc"

    def test_upload_file_with_spaces_in_name(self, client, sample_ifc_content):
        """Test that file names with spaces are handled correctly."""
        files = {"ifc_file": ("my model file.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "my model file.ifc"


# =============================================================================
# File Status Endpoint Tests
# =============================================================================


class TestFileStatusEndpoint:
    """Test file status endpoint (/api/status/{file_id})."""

    def test_status_returns_200_for_existing_file(self, client, uploaded_file_id):
        """Test that status endpoint returns 200 for existing file."""
        response = client.get(f"/api/status/{uploaded_file_id}")
        assert response.status_code == 200

    def test_status_returns_file_info(self, client, uploaded_file_id):
        """Test that status endpoint returns file information."""
        response = client.get(f"/api/status/{uploaded_file_id}")
        data = response.json()
        assert data["file_id"] == uploaded_file_id
        assert "original_filename" in data
        assert "file_size" in data
        assert "status" in data

    def test_status_returns_processing_status(self, client, uploaded_file_id):
        """Test that status endpoint returns processing status."""
        response = client.get(f"/api/status/{uploaded_file_id}")
        data = response.json()
        assert "processing_status" in data
        assert data["processing_status"] == "pending"

    def test_status_returns_404_for_unknown_file(self, client):
        """Test that status endpoint returns 404 for unknown file."""
        response = client.get("/api/status/unknown-file-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_status_returns_uploaded_at_timestamp(self, client, uploaded_file_id):
        """Test that status endpoint returns upload timestamp."""
        response = client.get(f"/api/status/{uploaded_file_id}")
        data = response.json()
        assert "uploaded_at" in data


# =============================================================================
# List Files Endpoint Tests
# =============================================================================


class TestListFilesEndpoint:
    """Test list files endpoint (/api/files)."""

    def test_list_files_returns_200(self, client):
        """Test that list files endpoint returns 200."""
        response = client.get("/api/files")
        assert response.status_code == 200

    def test_list_files_empty_initially(self, client):
        """Test that list files returns empty list initially."""
        response = client.get("/api/files")
        data = response.json()
        assert data["count"] == 0
        assert data["files"] == []

    def test_list_files_after_upload(self, client, uploaded_file_id):
        """Test that list files includes uploaded file."""
        response = client.get("/api/files")
        data = response.json()
        assert data["count"] == 1
        assert len(data["files"]) == 1
        assert data["files"][0]["file_id"] == uploaded_file_id

    def test_list_files_multiple_uploads(self, client, sample_ifc_content):
        """Test that list files includes all uploaded files."""
        # Upload multiple files
        for i in range(3):
            files = {"ifc_file": (f"model_{i}.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
            client.post("/api/upload", files=files)

        response = client.get("/api/files")
        data = response.json()
        assert data["count"] == 3
        assert len(data["files"]) == 3


# =============================================================================
# Delete File Endpoint Tests
# =============================================================================


class TestDeleteFileEndpoint:
    """Test delete file endpoint (/api/files/{file_id})."""

    def test_delete_file_returns_200(self, client, uploaded_file_id):
        """Test that deleting existing file returns 200."""
        response = client.delete(f"/api/files/{uploaded_file_id}")
        assert response.status_code == 200

    def test_delete_file_returns_success(self, client, uploaded_file_id):
        """Test that deleting file returns success message."""
        response = client.delete(f"/api/files/{uploaded_file_id}")
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()

    def test_delete_file_removes_from_tracking(self, client, uploaded_file_id):
        """Test that deleting file removes it from tracking."""
        client.delete(f"/api/files/{uploaded_file_id}")
        assert uploaded_file_id not in uploaded_files

    def test_delete_file_removes_from_disk(self, client, uploaded_file_id):
        """Test that deleting file removes it from disk."""
        file_path = Path(uploaded_files[uploaded_file_id]["file_path"])
        assert file_path.exists()
        client.delete(f"/api/files/{uploaded_file_id}")
        assert not file_path.exists()

    def test_delete_unknown_file_returns_404(self, client):
        """Test that deleting unknown file returns 404."""
        response = client.delete("/api/files/unknown-file-id")
        assert response.status_code == 404


# =============================================================================
# Cleanup Files Endpoint Tests
# =============================================================================


class TestCleanupFilesEndpoint:
    """Test cleanup files endpoint (DELETE /api/files)."""

    def test_cleanup_returns_200(self, client):
        """Test that cleanup endpoint returns 200."""
        response = client.delete("/api/files")
        assert response.status_code == 200

    def test_cleanup_empty_returns_success(self, client):
        """Test that cleanup with no files returns success."""
        response = client.delete("/api/files")
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 0

    def test_cleanup_deletes_all_files(self, client, sample_ifc_content):
        """Test that cleanup deletes all uploaded files."""
        # Upload multiple files
        file_ids = []
        for i in range(3):
            files = {"ifc_file": (f"model_{i}.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
            response = client.post("/api/upload", files=files)
            file_ids.append(response.json()["file_id"])

        # Cleanup
        response = client.delete("/api/files")
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 3
        assert len(uploaded_files) == 0


# =============================================================================
# Process Endpoint Tests
# =============================================================================


class TestProcessEndpoint:
    """Test process endpoint (/api/process/{file_id})."""

    def test_process_unknown_file_returns_404(self, client):
        """Test that processing unknown file returns 404."""
        response = client.post("/api/process/unknown-file-id")
        assert response.status_code == 404

    @patch("server.main.ifc_processor")
    def test_process_success_returns_200(self, mock_processor, client, uploaded_file_id):
        """Test that successful processing returns 200."""
        mock_result = ProcessingResult(
            success=True,
            output_format="json-mesh",
            output_path=None,
            output_data={"elements": []},
            processing_time_ms=100.0,
            element_count=10,
            vertex_count=1000,
            face_count=500,
            error=None,
            file_size_bytes=5000,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        assert response.status_code == 200

    @patch("server.main.ifc_processor")
    def test_process_returns_success_true(self, mock_processor, client, uploaded_file_id):
        """Test that successful processing returns success=True."""
        mock_result = ProcessingResult(
            success=True,
            output_format="json-mesh",
            output_path=None,
            output_data={"elements": []},
            processing_time_ms=100.0,
            element_count=10,
            vertex_count=1000,
            face_count=500,
            error=None,
            file_size_bytes=5000,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        data = response.json()
        assert data["success"] is True

    @patch("server.main.ifc_processor")
    def test_process_returns_file_info(self, mock_processor, client, uploaded_file_id):
        """Test that processing returns file information."""
        mock_result = ProcessingResult(
            success=True,
            output_format="json-mesh",
            output_path=None,
            output_data={"elements": []},
            processing_time_ms=100.0,
            element_count=10,
            vertex_count=1000,
            face_count=500,
            error=None,
            file_size_bytes=5000,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        data = response.json()
        assert data["file_id"] == uploaded_file_id
        assert "filename" in data

    @patch("server.main.ifc_processor")
    def test_process_returns_format(self, mock_processor, client, uploaded_file_id):
        """Test that processing returns output format."""
        mock_result = ProcessingResult(
            success=True,
            output_format="json-mesh",
            output_path=None,
            output_data={"elements": []},
            processing_time_ms=100.0,
            element_count=10,
            vertex_count=1000,
            face_count=500,
            error=None,
            file_size_bytes=5000,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        data = response.json()
        assert data["format"] == "json-mesh"

    @patch("server.main.ifc_processor")
    def test_process_returns_processing_time(self, mock_processor, client, uploaded_file_id):
        """Test that processing returns processing time."""
        mock_result = ProcessingResult(
            success=True,
            output_format="json-mesh",
            output_path=None,
            output_data={"elements": []},
            processing_time_ms=150.5,
            element_count=10,
            vertex_count=1000,
            face_count=500,
            error=None,
            file_size_bytes=5000,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        data = response.json()
        assert data["processing_time_ms"] == 150.5

    @patch("server.main.ifc_processor")
    def test_process_returns_stats(self, mock_processor, client, uploaded_file_id):
        """Test that processing returns geometry statistics."""
        mock_result = ProcessingResult(
            success=True,
            output_format="json-mesh",
            output_path=None,
            output_data={"elements": []},
            processing_time_ms=100.0,
            element_count=10,
            vertex_count=1000,
            face_count=500,
            error=None,
            file_size_bytes=5000,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        data = response.json()
        assert "stats" in data
        assert data["stats"]["elements"] == 10
        assert data["stats"]["vertices"] == 1000
        assert data["stats"]["faces"] == 500
        assert data["stats"]["output_size_bytes"] == 5000

    @patch("server.main.ifc_processor")
    def test_process_json_mesh_returns_geometry(self, mock_processor, client, uploaded_file_id):
        """Test that json-mesh format returns geometry data."""
        mock_result = ProcessingResult(
            success=True,
            output_format="json-mesh",
            output_path=None,
            output_data={"elements": [{"id": 1, "vertices": []}]},
            processing_time_ms=100.0,
            element_count=1,
            vertex_count=100,
            face_count=50,
            error=None,
            file_size_bytes=1000,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        data = response.json()
        assert "geometry" in data
        assert "elements" in data["geometry"]

    @patch("server.main.ifc_processor")
    def test_process_gltf_returns_download_path(self, mock_processor, client, uploaded_file_id):
        """Test that gltf format returns download path."""
        mock_result = ProcessingResult(
            success=True,
            output_format="gltf",
            output_path="/tmp/output.glb",
            output_data=None,
            processing_time_ms=100.0,
            element_count=10,
            vertex_count=1000,
            face_count=500,
            error=None,
            file_size_bytes=10000,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        data = response.json()
        assert "output_file" in data
        assert f"/api/download/{uploaded_file_id}" in data["output_file"]

    @patch("server.main.ifc_processor")
    def test_process_failure_returns_500(self, mock_processor, client, uploaded_file_id):
        """Test that processing failure returns 500."""
        mock_result = ProcessingResult(
            success=False,
            output_format="json-mesh",
            output_path=None,
            output_data=None,
            processing_time_ms=50.0,
            element_count=0,
            vertex_count=0,
            face_count=0,
            error="Failed to parse IFC file",
            file_size_bytes=0,
        )
        mock_processor.process.return_value = mock_result

        response = client.post(f"/api/process/{uploaded_file_id}")
        assert response.status_code == 500
        assert "Failed to parse IFC file" in response.json()["detail"]

    @patch("server.main.ifc_processor")
    def test_process_updates_file_tracking(self, mock_processor, client, uploaded_file_id):
        """Test that processing updates file tracking info."""
        mock_result = ProcessingResult(
            success=True,
            output_format="json-mesh",
            output_path=None,
            output_data={"elements": []},
            processing_time_ms=100.0,
            element_count=10,
            vertex_count=1000,
            face_count=500,
            error=None,
            file_size_bytes=5000,
        )
        mock_processor.process.return_value = mock_result

        client.post(f"/api/process/{uploaded_file_id}")

        file_info = uploaded_files[uploaded_file_id]
        assert file_info["processing_status"] == "completed"
        assert "processing_result" in file_info

    def test_process_with_output_format_query_param(self, client, uploaded_file_id):
        """Test that output_format query parameter is accepted."""
        with patch("server.main.ifc_processor") as mock_processor:
            mock_result = ProcessingResult(
                success=True,
                output_format="json-mesh",
                output_path=None,
                output_data={"elements": []},
                processing_time_ms=100.0,
                element_count=10,
                vertex_count=1000,
                face_count=500,
                error=None,
                file_size_bytes=5000,
            )
            mock_processor.process.return_value = mock_result

            response = client.post(f"/api/process/{uploaded_file_id}?output_format=json-mesh")
            assert response.status_code == 200
            mock_processor.process.assert_called_once()
            call_kwargs = mock_processor.process.call_args
            assert call_kwargs[1]["preferred_format"] == "json-mesh"

    def test_process_deleted_ifc_file_returns_404(self, client, uploaded_file_id):
        """Test that processing returns 404 if IFC file was deleted from disk."""
        # Delete the file from disk but keep tracking info
        file_path = Path(uploaded_files[uploaded_file_id]["file_path"])
        file_path.unlink()

        response = client.post(f"/api/process/{uploaded_file_id}")
        assert response.status_code == 404
        assert "no longer exists" in response.json()["detail"]


# =============================================================================
# Download Endpoint Tests
# =============================================================================


class TestDownloadEndpoint:
    """Test download endpoint (/api/download/{file_id})."""

    def test_download_unknown_file_returns_404(self, client):
        """Test that downloading unknown file returns 404."""
        response = client.get("/api/download/unknown-file-id")
        assert response.status_code == 404

    def test_download_unprocessed_file_returns_404(self, client, uploaded_file_id):
        """Test that downloading unprocessed file returns 404."""
        response = client.get(f"/api/download/{uploaded_file_id}")
        assert response.status_code == 404
        assert "not yet processed" in response.json()["detail"]

    @patch("server.main.ifc_processor")
    def test_download_processed_file_returns_200(self, mock_processor, client, uploaded_file_id):
        """Test that downloading processed file returns 200."""
        # Create a temp file to serve as processed output
        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            f.write(b"glTF binary content")
            temp_path = f.name

        try:
            mock_result = ProcessingResult(
                success=True,
                output_format="gltf",
                output_path=temp_path,
                output_data=None,
                processing_time_ms=100.0,
                element_count=10,
                vertex_count=1000,
                face_count=500,
                error=None,
                file_size_bytes=20,
            )
            mock_processor.process.return_value = mock_result

            # Process the file
            client.post(f"/api/process/{uploaded_file_id}")

            # Download the processed file
            response = client.get(f"/api/download/{uploaded_file_id}")
            assert response.status_code == 200
            assert response.content == b"glTF binary content"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("server.main.ifc_processor")
    def test_download_glb_returns_correct_media_type(self, mock_processor, client, uploaded_file_id):
        """Test that downloading .glb file returns correct media type."""
        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            f.write(b"glTF binary content")
            temp_path = f.name

        try:
            mock_result = ProcessingResult(
                success=True,
                output_format="gltf",
                output_path=temp_path,
                output_data=None,
                processing_time_ms=100.0,
                element_count=10,
                vertex_count=1000,
                face_count=500,
                error=None,
                file_size_bytes=20,
            )
            mock_processor.process.return_value = mock_result

            client.post(f"/api/process/{uploaded_file_id}")
            response = client.get(f"/api/download/{uploaded_file_id}")
            assert response.headers["content-type"] == "model/gltf-binary"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("server.main.ifc_processor")
    def test_download_gltf_returns_correct_media_type(self, mock_processor, client, uploaded_file_id):
        """Test that downloading .gltf file returns correct media type."""
        with tempfile.NamedTemporaryFile(suffix=".gltf", delete=False) as f:
            f.write(b'{"asset": {"version": "2.0"}}')
            temp_path = f.name

        try:
            mock_result = ProcessingResult(
                success=True,
                output_format="gltf",
                output_path=temp_path,
                output_data=None,
                processing_time_ms=100.0,
                element_count=10,
                vertex_count=1000,
                face_count=500,
                error=None,
                file_size_bytes=30,
            )
            mock_processor.process.return_value = mock_result

            client.post(f"/api/process/{uploaded_file_id}")
            response = client.get(f"/api/download/{uploaded_file_id}")
            assert response.headers["content-type"] == "model/gltf+json"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("server.main.ifc_processor")
    def test_download_deleted_processed_file_returns_404(self, mock_processor, client, uploaded_file_id):
        """Test that downloading deleted processed file returns 404."""
        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            f.write(b"glTF binary content")
            temp_path = f.name

        try:
            mock_result = ProcessingResult(
                success=True,
                output_format="gltf",
                output_path=temp_path,
                output_data=None,
                processing_time_ms=100.0,
                element_count=10,
                vertex_count=1000,
                face_count=500,
                error=None,
                file_size_bytes=20,
            )
            mock_processor.process.return_value = mock_result

            client.post(f"/api/process/{uploaded_file_id}")

            # Delete the processed file from disk
            os.unlink(temp_path)

            response = client.get(f"/api/download/{uploaded_file_id}")
            assert response.status_code == 404
            assert "no longer exists" in response.json()["detail"]
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# =============================================================================
# Capabilities Endpoint Tests
# =============================================================================


class TestCapabilitiesEndpoint:
    """Test capabilities endpoint (/api/capabilities)."""

    def test_capabilities_returns_200(self, client):
        """Test that capabilities endpoint returns 200."""
        response = client.get("/api/capabilities")
        assert response.status_code == 200

    def test_capabilities_returns_formats(self, client):
        """Test that capabilities returns format information."""
        response = client.get("/api/capabilities")
        data = response.json()
        assert "formats" in data
        assert "gltf" in data["formats"]
        assert "json-mesh" in data["formats"]

    def test_capabilities_gltf_format_info(self, client):
        """Test that capabilities returns gltf format details."""
        response = client.get("/api/capabilities")
        data = response.json()
        gltf = data["formats"]["gltf"]
        assert "available" in gltf
        assert "description" in gltf
        assert "file_extension" in gltf

    def test_capabilities_json_mesh_format_info(self, client):
        """Test that capabilities returns json-mesh format details."""
        response = client.get("/api/capabilities")
        data = response.json()
        json_mesh = data["formats"]["json-mesh"]
        assert json_mesh["available"] is True
        assert "description" in json_mesh

    def test_capabilities_returns_recommended_format(self, client):
        """Test that capabilities returns recommended format."""
        response = client.get("/api/capabilities")
        data = response.json()
        assert "recommended_format" in data
        assert data["recommended_format"] in ["gltf", "json-mesh"]

    def test_capabilities_returns_processor_info(self, client):
        """Test that capabilities returns processor information."""
        response = client.get("/api/capabilities")
        data = response.json()
        assert "processor" in data


# =============================================================================
# Constants Tests
# =============================================================================


class TestServerConstants:
    """Test server module constants."""

    def test_max_file_size_is_500mb(self):
        """Test that MAX_FILE_SIZE is 500MB."""
        assert MAX_FILE_SIZE == 500 * 1024 * 1024

    def test_upload_dir_exists(self):
        """Test that UPLOAD_DIR exists."""
        assert UPLOAD_DIR.exists()

    def test_processed_dir_exists(self):
        """Test that PROCESSED_DIR exists."""
        assert PROCESSED_DIR.exists()


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

    def test_cors_allows_localhost_8080(self, client):
        """Test that CORS allows requests from localhost:8080."""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI returns 200 for OPTIONS preflight
        assert response.status_code == 200

    def test_cors_allows_127_0_0_1_8080(self, client):
        """Test that CORS allows requests from 127.0.0.1:8080."""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://127.0.0.1:8080",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_upload_without_file_returns_422(self, client):
        """Test that upload without file returns 422."""
        response = client.post("/api/upload")
        assert response.status_code == 422

    def test_very_long_filename(self, client, sample_ifc_content):
        """Test handling of very long filenames."""
        long_name = "a" * 200 + ".ifc"
        files = {"ifc_file": (long_name, io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200

    def test_unicode_filename(self, client, sample_ifc_content):
        """Test handling of unicode characters in filename."""
        files = {"ifc_file": ("模型文件.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200

    def test_special_characters_filename(self, client, sample_ifc_content):
        """Test handling of special characters in filename."""
        files = {"ifc_file": ("model-v1.2_final(2).ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200

    def test_process_invalid_output_format(self, client, uploaded_file_id):
        """Test that invalid output_format query param is rejected."""
        response = client.post(f"/api/process/{uploaded_file_id}?output_format=invalid")
        assert response.status_code == 422  # Validation error
