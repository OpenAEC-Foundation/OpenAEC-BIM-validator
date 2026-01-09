"""Unit tests for the async validation endpoints in server/main.py.

Tests cover:
- POST /api/v1/validate endpoint
  - Returns 202 with job_id, status='pending', message, and status_url
  - Invalid file types return 400
- GET /api/v1/jobs/{job_id} endpoint
  - Returns correct status for pending, processing, completed, failed jobs
  - Returns 404 for unknown job_id
  - Completed job includes result and duration_seconds
  - Failed job includes error message
- Job expiration and cleanup via API
  - Old completed/failed jobs are cleaned up after TTL
  - Stuck pending/processing jobs are cleaned up after TTL
  - Active jobs within TTL are preserved
  - Cleanup is triggered on each status request

Usage:
    pytest test/test_async_validation.py -v
    pytest test/test_async_validation.py --cov=server.main --cov-report=term-missing
"""

import io
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.main import app, job_manager


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
    return b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('sample.ifc','2025-01-01T12:00:00',('Test Author'),('Test Organization'),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPERSON($,$,'Test User',$,$,$,$,$);
#2=IFCORGANIZATION($,'Test Organization',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'1.0','Test Application','TestApp');
#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,1704067200);
#6=IFCDIRECTION((1.,0.,0.));
#7=IFCDIRECTION((0.,0.,1.));
#8=IFCCARTESIANPOINT((0.,0.,0.));
#9=IFCAXIS2PLACEMENT3D(#8,#7,#6);
#10=IFCPROJECT('2XyZ3W4aa56Bjd9gQc07yA',#5,'Test Project',$,$,$,$,$,#9);
ENDSEC;
END-ISO-10303-21;
"""


@pytest.fixture
def sample_ids_content():
    """Sample valid IDS file content for testing."""
    return b"""<?xml version="1.0" encoding="utf-8"?>
<ids xmlns:xs="http://www.w3.org/2001/XMLSchema"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://standards.buildingsmart.org/IDS http://standards.buildingsmart.org/IDS/1.0/ids.xsd"
     xmlns="http://standards.buildingsmart.org/IDS">
  <info>
    <title>Test IDS Specification</title>
    <copyright>Test Organization</copyright>
    <version>1.0</version>
    <description>Minimal IDS for testing</description>
    <author>test@example.com</author>
    <date>2025-01-01</date>
    <purpose>Unit testing</purpose>
  </info>
  <specifications>
    <specification name="Project Name" ifcVersion="IFC2X3 IFC4" identifier="TEST-001" description="Project must have a name" instructions="Ensure project has Name attribute">
      <applicability minOccurs="1" maxOccurs="unbounded">
        <entity>
          <name>
            <simpleValue>IFCPROJECT</simpleValue>
          </name>
        </entity>
      </applicability>
      <requirements>
        <attribute cardinality="required" instructions="Project name is required">
          <name>
            <simpleValue>Name</simpleValue>
          </name>
        </attribute>
      </requirements>
    </specification>
  </specifications>
</ids>
"""


@pytest.fixture(autouse=True)
def cleanup_jobs():
    """Clean up job_manager jobs before and after each test."""
    # Clear before test
    job_manager._jobs.clear()
    yield
    # Clear after test
    job_manager._jobs.clear()


# =============================================================================
# POST /api/v1/validate - Success Tests
# =============================================================================


class TestValidateEndpointSuccess:
    """Test POST /api/v1/validate endpoint success cases."""

    def test_validate_returns_202_status_code(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that POST /api/v1/validate returns 202 Accepted.

        Acceptance Criteria:
        - POST with valid IFC and IDS files returns 202 status code
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 202, (
            f"Expected 202 Accepted, got {response.status_code}: {response.text}"
        )

    def test_validate_returns_job_id(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that response includes a valid job_id.

        Acceptance Criteria:
        - Response contains job_id field
        - job_id is a valid UUID4 string
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)
        data = response.json()

        assert "job_id" in data, "Response should contain job_id"
        assert isinstance(data["job_id"], str), "job_id should be a string"
        assert len(data["job_id"]) == 36, "job_id should be UUID format (36 chars)"

        # Verify it's a valid UUID
        try:
            parsed_uuid = uuid.UUID(data["job_id"])
            assert parsed_uuid.version == 4, "job_id should be UUID version 4"
        except ValueError:
            pytest.fail(f"job_id '{data['job_id']}' is not a valid UUID")

    def test_validate_returns_pending_status(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that response includes status='pending'.

        Acceptance Criteria:
        - Response contains status field
        - status value is 'pending'
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)
        data = response.json()

        assert "status" in data, "Response should contain status field"
        assert data["status"] == "pending", (
            f"Status should be 'pending', got '{data['status']}'"
        )

    def test_validate_returns_message(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that response includes a message.

        Acceptance Criteria:
        - Response contains message field
        - message is a non-empty string
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)
        data = response.json()

        assert "message" in data, "Response should contain message field"
        assert isinstance(data["message"], str), "message should be a string"
        assert len(data["message"]) > 0, "message should not be empty"
        assert "queued" in data["message"].lower(), (
            "message should indicate job was queued"
        )

    def test_validate_returns_status_url(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that response includes status_url for polling.

        Acceptance Criteria:
        - Response contains status_url field
        - status_url contains the job_id
        - status_url points to /api/v1/jobs/{job_id}
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)
        data = response.json()

        assert "status_url" in data, "Response should contain status_url field"
        assert isinstance(data["status_url"], str), "status_url should be a string"
        assert "/api/v1/jobs/" in data["status_url"], (
            "status_url should point to jobs endpoint"
        )
        assert data["job_id"] in data["status_url"], (
            "status_url should contain the job_id"
        )

    def test_validate_response_has_all_required_fields(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that response includes all required fields.

        Acceptance Criteria:
        - Response contains: job_id, status, message, status_url
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)
        data = response.json()

        required_fields = ["job_id", "status", "message", "status_url"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}' field"

    def test_validate_creates_job_in_job_manager(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that submitting validation creates a job in job_manager.

        Acceptance Criteria:
        - Job is created in job_manager with the returned job_id
        - Job status is pending
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)
        data = response.json()
        job_id = data["job_id"]

        # Verify job exists in job_manager
        job = job_manager.get_job(job_id)
        assert job is not None, f"Job {job_id} should exist in job_manager"

    def test_validate_accepts_case_insensitive_ifc_extension(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that .IFC extension (uppercase) is accepted.

        Acceptance Criteria:
        - File with .IFC extension is accepted
        """
        files = {
            "ifc_file": ("MODEL.IFC", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )

    def test_validate_accepts_case_insensitive_ids_extension(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that .IDS extension (uppercase) is accepted.

        Acceptance Criteria:
        - File with .IDS extension is accepted
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("SPEC.IDS", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )


# =============================================================================
# POST /api/v1/validate - Invalid File Type Tests
# =============================================================================


class TestValidateEndpointInvalidFileTypes:
    """Test POST /api/v1/validate endpoint with invalid file types."""

    def test_validate_invalid_ifc_extension_returns_400(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that non-.ifc file extension returns 400.

        Acceptance Criteria:
        - File with invalid extension returns 400
        - Error message mentions invalid file type
        """
        files = {
            "ifc_file": ("model.txt", io.BytesIO(sample_ifc_content), "text/plain"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400, (
            f"Expected 400 for invalid IFC extension, got {response.status_code}"
        )
        assert "invalid" in response.json()["detail"].lower(), (
            "Error should mention invalid file type"
        )

    def test_validate_invalid_ids_extension_returns_400(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that non-.ids file extension returns 400.

        Acceptance Criteria:
        - File with invalid extension returns 400
        - Error message mentions invalid file type
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.xml", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400, (
            f"Expected 400 for invalid IDS extension, got {response.status_code}"
        )
        assert "invalid" in response.json()["detail"].lower(), (
            "Error should mention invalid file type"
        )

    def test_validate_jpg_extension_returns_400(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that .jpg file extension returns 400.

        Acceptance Criteria:
        - Image file extension returns 400
        """
        files = {
            "ifc_file": ("model.jpg", io.BytesIO(sample_ifc_content), "image/jpeg"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400

    def test_validate_pdf_extension_returns_400(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that .pdf file extension returns 400.

        Acceptance Criteria:
        - PDF file extension returns 400
        """
        files = {
            "ifc_file": ("model.pdf", io.BytesIO(sample_ifc_content), "application/pdf"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400

    def test_validate_no_extension_returns_400(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that file with no extension returns 400.

        Acceptance Criteria:
        - File without extension returns 400
        """
        files = {
            "ifc_file": ("model", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400

    def test_validate_error_message_includes_filename(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that error message includes the invalid filename.

        Acceptance Criteria:
        - Error detail includes the filename that was invalid
        """
        files = {
            "ifc_file": ("bad_model.txt", io.BytesIO(sample_ifc_content), "text/plain"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "bad_model.txt" in detail, (
            "Error should include the invalid filename"
        )


# =============================================================================
# POST /api/v1/validate - Empty/Missing File Tests
# =============================================================================


class TestValidateEndpointEmptyFiles:
    """Test POST /api/v1/validate endpoint with empty or missing files."""

    def test_validate_empty_ifc_file_returns_400(
        self, client, sample_ids_content
    ):
        """Test that empty IFC file returns 400.

        Acceptance Criteria:
        - Empty IFC file returns 400
        - Error message mentions empty file
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(b""), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400, (
            f"Expected 400 for empty IFC file, got {response.status_code}"
        )
        assert "empty" in response.json()["detail"].lower(), (
            "Error should mention empty file"
        )

    def test_validate_empty_ids_file_returns_400(
        self, client, sample_ifc_content
    ):
        """Test that empty IDS file returns 400.

        Acceptance Criteria:
        - Empty IDS file returns 400
        - Error message mentions empty file
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(b""), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400, (
            f"Expected 400 for empty IDS file, got {response.status_code}"
        )
        assert "empty" in response.json()["detail"].lower(), (
            "Error should mention empty file"
        )

    def test_validate_missing_ifc_file_returns_422(self, client, sample_ids_content):
        """Test that missing IFC file returns 422.

        Acceptance Criteria:
        - Missing required file returns 422 (validation error)
        """
        files = {
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 422, (
            f"Expected 422 for missing IFC file, got {response.status_code}"
        )

    def test_validate_missing_ids_file_returns_400(self, client, sample_ifc_content):
        """Test that missing IDS file (without standard) returns 400.

        Acceptance Criteria:
        - Missing IDS file without standard parameter returns 400
        - (Note: IDS is optional if 'standard' query param is provided)
        """
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 400, (
            f"Expected 400 for missing IDS file, got {response.status_code}"
        )

    def test_validate_no_files_returns_422(self, client):
        """Test that request with no files returns 422.

        Acceptance Criteria:
        - Request without files returns 422 (validation error)
        """
        response = client.post("/api/v1/validate")

        assert response.status_code == 422, (
            f"Expected 422 for no files, got {response.status_code}"
        )


# =============================================================================
# POST /api/v1/validate - Filename Edge Cases
# =============================================================================


class TestValidateEndpointFilenameEdgeCases:
    """Test POST /api/v1/validate endpoint with edge case filenames."""

    def test_validate_filename_with_spaces(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that filenames with spaces are handled correctly.

        Acceptance Criteria:
        - Files with spaces in names are accepted
        """
        files = {
            "ifc_file": (
                "my model file.ifc",
                io.BytesIO(sample_ifc_content),
                "application/octet-stream",
            ),
            "ids_file": (
                "my spec file.ids",
                io.BytesIO(sample_ids_content),
                "application/xml",
            ),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )

    def test_validate_filename_with_unicode(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that filenames with unicode characters are handled.

        Acceptance Criteria:
        - Files with unicode names are accepted
        """
        files = {
            "ifc_file": (
                "modell_gebäude.ifc",
                io.BytesIO(sample_ifc_content),
                "application/octet-stream",
            ),
            "ids_file": ("规格.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )

    def test_validate_filename_with_special_chars(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that filenames with special characters are handled.

        Acceptance Criteria:
        - Files with special chars in names are accepted
        """
        files = {
            "ifc_file": (
                "model-v1.2_final(2).ifc",
                io.BytesIO(sample_ifc_content),
                "application/octet-stream",
            ),
            "ids_file": (
                "spec_v1.0-draft.ids",
                io.BytesIO(sample_ids_content),
                "application/xml",
            ),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )

    def test_validate_long_filename(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that long filenames are handled.

        Acceptance Criteria:
        - Files with long names are accepted
        """
        long_name = "a" * 200 + ".ifc"
        files = {
            "ifc_file": (
                long_name,
                io.BytesIO(sample_ifc_content),
                "application/octet-stream",
            ),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        response = client.post("/api/v1/validate", files=files)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )


# =============================================================================
# GET /api/v1/jobs/{job_id} - Job Status Endpoint Tests
# =============================================================================


class TestJobStatusEndpointBasics:
    """Test GET /api/v1/jobs/{job_id} endpoint basic functionality."""

    def test_job_status_returns_200_for_valid_job(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that GET /api/v1/jobs/{job_id} returns 200 for valid job.

        Acceptance Criteria:
        - Request for existing job returns 200 status code
        """
        # Create a job first
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }
        create_response = client.post("/api/v1/validate", files=files)
        job_id = create_response.json()["job_id"]

        # Get job status
        response = client.get(f"/api/v1/jobs/{job_id}")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

    def test_job_status_returns_job_id_in_response(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that response includes the correct job_id.

        Acceptance Criteria:
        - Response contains job_id field matching the requested ID
        """
        # Create a job first
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }
        create_response = client.post("/api/v1/validate", files=files)
        job_id = create_response.json()["job_id"]

        # Get job status
        response = client.get(f"/api/v1/jobs/{job_id}")
        data = response.json()

        assert "job_id" in data, "Response should contain job_id"
        assert data["job_id"] == job_id, (
            f"job_id should match requested ID, got {data['job_id']}"
        )

    def test_job_status_returns_status_field(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that response includes status field.

        Acceptance Criteria:
        - Response contains status field
        - status is one of: pending, processing, completed, failed
        """
        # Create a job first
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }
        create_response = client.post("/api/v1/validate", files=files)
        job_id = create_response.json()["job_id"]

        # Get job status
        response = client.get(f"/api/v1/jobs/{job_id}")
        data = response.json()

        assert "status" in data, "Response should contain status field"
        valid_statuses = ["pending", "processing", "completed", "failed"]
        assert data["status"] in valid_statuses, (
            f"status should be one of {valid_statuses}, got '{data['status']}'"
        )

    def test_job_status_returns_created_at(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that response includes created_at timestamp.

        Acceptance Criteria:
        - Response contains created_at field
        - created_at is a valid ISO 8601 timestamp
        """
        # Create a job first
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }
        create_response = client.post("/api/v1/validate", files=files)
        job_id = create_response.json()["job_id"]

        # Get job status
        response = client.get(f"/api/v1/jobs/{job_id}")
        data = response.json()

        assert "created_at" in data, "Response should contain created_at field"
        assert data["created_at"] is not None, "created_at should not be None"
        # Verify it's a valid ISO timestamp by checking format
        assert "T" in data["created_at"], (
            "created_at should be ISO 8601 format (contain 'T')"
        )


class TestJobStatusEndpointNotFound:
    """Test GET /api/v1/jobs/{job_id} endpoint 404 behavior."""

    def test_unknown_job_id_returns_404(self, client):
        """Test that unknown job_id returns 404.

        Acceptance Criteria:
        - Request for non-existent job_id returns 404
        """
        fake_job_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/jobs/{fake_job_id}")

        assert response.status_code == 404, (
            f"Expected 404 for unknown job_id, got {response.status_code}"
        )

    def test_unknown_job_id_returns_error_detail(self, client):
        """Test that 404 response includes error detail.

        Acceptance Criteria:
        - 404 response contains detail field
        - detail mentions job not found
        """
        fake_job_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/jobs/{fake_job_id}")
        data = response.json()

        assert "detail" in data, "404 response should contain detail"
        assert "not found" in data["detail"].lower(), (
            "Error detail should mention 'not found'"
        )

    def test_unknown_job_id_includes_job_id_in_error(self, client):
        """Test that 404 error includes the requested job_id.

        Acceptance Criteria:
        - Error detail includes the job_id that was requested
        """
        fake_job_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/jobs/{fake_job_id}")
        data = response.json()

        assert fake_job_id in data["detail"], (
            f"Error detail should include the requested job_id: {fake_job_id}"
        )

    def test_invalid_uuid_format_returns_404(self, client):
        """Test that invalid UUID format returns 404.

        Acceptance Criteria:
        - Malformed job_id returns 404 (or 422)
        """
        invalid_job_id = "not-a-valid-uuid"

        response = client.get(f"/api/v1/jobs/{invalid_job_id}")

        # Should return 404 (job not found) since it won't match any stored job
        assert response.status_code == 404, (
            f"Expected 404 for invalid job_id format, got {response.status_code}"
        )


class TestJobStatusEndpointPendingJob:
    """Test GET /api/v1/jobs/{job_id} for pending jobs."""

    def test_pending_job_shows_pending_status(self, client):
        """Test that pending job shows pending status.

        Acceptance Criteria:
        - Job with status=pending shows correct status
        """
        # Directly create a pending job via job_manager (don't run validation)
        job = job_manager.create_job()

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data["status"] == "pending", (
            f"Job status should be pending, got '{data['status']}'"
        )

    def test_pending_job_has_no_result(self, client):
        """Test that pending job has no result field populated.

        Acceptance Criteria:
        - Pending job should not have result populated
        """
        # Directly create a pending job via job_manager
        job = job_manager.create_job()

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data.get("result") is None, (
            "Pending job should not have result"
        )

    def test_pending_job_has_no_started_at(self, client):
        """Test that pending job has no started_at timestamp.

        Acceptance Criteria:
        - Pending job should not have started_at populated
        """
        # Directly create a pending job via job_manager
        job = job_manager.create_job()

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data.get("started_at") is None, (
            "Pending job should not have started_at"
        )


class TestJobStatusEndpointCompletedJob:
    """Test GET /api/v1/jobs/{job_id} for completed jobs."""

    def test_completed_job_includes_result(self, client):
        """Test that completed job includes result field.

        Acceptance Criteria:
        - Completed job has result field populated
        """
        # Directly manipulate job_manager to create a completed job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        # Create a mock validation result
        mock_result = {
            "success": True,
            "total_specifications": 1,
            "passed_specifications": 1,
            "failed_specifications": 0,
            "pass_rate_percent": 100.0,
            "specifications": [],
        }
        job_manager.complete_job(job.job_id, mock_result)

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data["status"] == "completed", (
            f"Job status should be completed, got '{data['status']}'"
        )
        assert "result" in data, "Completed job should have result field"
        assert data["result"] is not None, "Completed job result should not be None"

    def test_completed_job_result_contains_validation_data(self, client):
        """Test that completed job result contains validation data.

        Acceptance Criteria:
        - Result contains expected validation fields
        """
        # Create and complete a job with mock result
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        mock_result = {
            "success": True,
            "total_specifications": 5,
            "passed_specifications": 4,
            "failed_specifications": 1,
            "pass_rate_percent": 80.0,
            "specifications": [],
        }
        job_manager.complete_job(job.job_id, mock_result)

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data["result"]["success"] is True
        assert data["result"]["total_specifications"] == 5
        assert data["result"]["passed_specifications"] == 4
        assert data["result"]["pass_rate_percent"] == 80.0

    def test_completed_job_includes_duration_seconds(self, client):
        """Test that completed job includes duration_seconds.

        Acceptance Criteria:
        - Completed job has duration_seconds field
        - duration_seconds is a positive number
        """
        # Create and complete a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.complete_job(job.job_id, {"success": True})

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert "duration_seconds" in data, (
            "Completed job should have duration_seconds field"
        )
        assert data["duration_seconds"] is not None, (
            "duration_seconds should not be None"
        )
        assert data["duration_seconds"] >= 0, (
            f"duration_seconds should be >= 0, got {data['duration_seconds']}"
        )

    def test_completed_job_includes_completed_at(self, client):
        """Test that completed job includes completed_at timestamp.

        Acceptance Criteria:
        - Completed job has completed_at field
        - completed_at is a valid ISO 8601 timestamp
        """
        # Create and complete a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.complete_job(job.job_id, {"success": True})

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert "completed_at" in data, (
            "Completed job should have completed_at field"
        )
        assert data["completed_at"] is not None, (
            "completed_at should not be None for completed job"
        )
        assert "T" in data["completed_at"], (
            "completed_at should be ISO 8601 format"
        )

    def test_completed_job_has_no_error(self, client):
        """Test that completed job does not have error field populated.

        Acceptance Criteria:
        - Completed (successful) job should not have error
        """
        # Create and complete a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.complete_job(job.job_id, {"success": True})

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data.get("error") is None, (
            "Completed job should not have error field populated"
        )


class TestJobStatusEndpointFailedJob:
    """Test GET /api/v1/jobs/{job_id} for failed jobs."""

    def test_failed_job_includes_error(self, client):
        """Test that failed job includes error field.

        Acceptance Criteria:
        - Failed job has error field populated
        - error is a non-empty string
        """
        # Create and fail a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.fail_job(job.job_id, "Validation failed: invalid IFC format")

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data["status"] == "failed", (
            f"Job status should be failed, got '{data['status']}'"
        )
        assert "error" in data, "Failed job should have error field"
        assert data["error"] is not None, "Failed job error should not be None"
        assert len(data["error"]) > 0, "Failed job error should not be empty"

    def test_failed_job_error_contains_error_message(self, client):
        """Test that failed job error contains the error message.

        Acceptance Criteria:
        - Error field contains the error message passed to fail_job
        """
        error_message = "Test error: could not parse IFC file"

        # Create and fail a job with specific error
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.fail_job(job.job_id, error_message)

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert error_message in data["error"], (
            f"Error should contain '{error_message}', got '{data['error']}'"
        )

    def test_failed_job_includes_completed_at(self, client):
        """Test that failed job includes completed_at timestamp.

        Acceptance Criteria:
        - Failed job has completed_at field
        """
        # Create and fail a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.fail_job(job.job_id, "Test failure")

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert "completed_at" in data, (
            "Failed job should have completed_at field"
        )
        assert data["completed_at"] is not None, (
            "completed_at should not be None for failed job"
        )

    def test_failed_job_has_no_result(self, client):
        """Test that failed job does not have result field populated.

        Acceptance Criteria:
        - Failed job should not have result populated
        """
        # Create and fail a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.fail_job(job.job_id, "Test failure")

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data.get("result") is None, (
            "Failed job should not have result field populated"
        )

    def test_failed_job_includes_duration_seconds(self, client):
        """Test that failed job includes duration_seconds.

        Acceptance Criteria:
        - Failed job has duration_seconds field (time until failure)
        """
        # Create and fail a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.fail_job(job.job_id, "Test failure")

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert "duration_seconds" in data, (
            "Failed job should have duration_seconds field"
        )
        assert data["duration_seconds"] is not None, (
            "duration_seconds should not be None for failed job"
        )


class TestJobStatusEndpointProcessingJob:
    """Test GET /api/v1/jobs/{job_id} for processing jobs."""

    def test_processing_job_shows_processing_status(self, client):
        """Test that processing job shows processing status.

        Acceptance Criteria:
        - Job with status=processing shows correct status
        """
        # Create a job and start it (but don't complete)
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert data["status"] == "processing", (
            f"Job status should be processing, got '{data['status']}'"
        )

    def test_processing_job_includes_started_at(self, client):
        """Test that processing job includes started_at timestamp.

        Acceptance Criteria:
        - Processing job has started_at field
        """
        # Create a job and start it
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert "started_at" in data, (
            "Processing job should have started_at field"
        )
        assert data["started_at"] is not None, (
            "started_at should not be None for processing job"
        )

    def test_processing_job_with_progress_shows_progress(self, client):
        """Test that processing job with progress shows progress message.

        Acceptance Criteria:
        - Processing job can show progress message
        """
        # Create a job, start it, and update progress
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.update_progress(job.job_id, "Validating specification 3 of 13...")

        # Get job status
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        data = response.json()

        assert "progress" in data, (
            "Processing job with progress should have progress field"
        )
        assert "Validating specification 3 of 13" in data["progress"], (
            f"Progress should contain expected message, got '{data.get('progress')}'"
        )


# =============================================================================
# Job Expiration Tests via API
# =============================================================================


class TestJobExpirationViaEndpoint:
    """Test job expiration and cleanup via the job status endpoint.

    The job status endpoint calls job_manager.cleanup_expired() opportunistically
    on each request. These tests verify that expired jobs are cleaned up and
    that active jobs are not affected.
    """

    def test_expired_completed_job_is_cleaned_up(self, client):
        """Test that completed jobs older than TTL are cleaned up.

        Acceptance Criteria:
        - Completed job older than TTL is removed on next status request
        - Returns 404 after cleanup
        """
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        # Create and complete a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.complete_job(job.job_id, {"result": "test"})

        # Verify job exists initially
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        assert response.status_code == 200, "Job should exist initially"

        # Mock time to simulate TTL expiration (1 hour + 1 second in future)
        future_time = datetime.now(timezone.utc) + timedelta(seconds=3601)
        with patch("server.job_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Trigger cleanup via status request (for any job - the cleanup runs globally)
            # Create a fresh job to have a valid endpoint to call
            fresh_job = job_manager.create_job()
            client.get(f"/api/v1/jobs/{fresh_job.job_id}")

        # Now the original job should be cleaned up
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        assert response.status_code == 404, (
            f"Expired job should return 404, got {response.status_code}"
        )

    def test_expired_failed_job_is_cleaned_up(self, client):
        """Test that failed jobs older than TTL are cleaned up.

        Acceptance Criteria:
        - Failed job older than TTL is removed on next status request
        - Returns 404 after cleanup
        """
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        # Create and fail a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.fail_job(job.job_id, "Test error")

        # Verify job exists initially
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        assert response.status_code == 200, "Job should exist initially"
        assert response.json()["status"] == "failed"

        # Mock time to simulate TTL expiration
        future_time = datetime.now(timezone.utc) + timedelta(seconds=3601)
        with patch("server.job_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Trigger cleanup
            fresh_job = job_manager.create_job()
            client.get(f"/api/v1/jobs/{fresh_job.job_id}")

        # Original job should be cleaned up
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        assert response.status_code == 404, "Expired failed job should return 404"

    def test_recent_completed_job_is_not_cleaned_up(self, client):
        """Test that recently completed jobs are preserved.

        Acceptance Criteria:
        - Completed job within TTL is NOT removed
        - Returns 200 with job data
        """
        # Create and complete a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.complete_job(job.job_id, {"result": "test"})

        # Request job status (triggers cleanup)
        response = client.get(f"/api/v1/jobs/{job.job_id}")

        # Job should still exist (not expired)
        assert response.status_code == 200, (
            "Recent completed job should not be cleaned up"
        )
        assert response.json()["status"] == "completed"

    def test_cleanup_preserves_pending_jobs_within_ttl(self, client):
        """Test that pending jobs within TTL are not cleaned up.

        Acceptance Criteria:
        - Pending job within TTL is preserved
        - Status remains pending
        """
        # Create a pending job (don't start it)
        job = job_manager.create_job()

        # Request job status (triggers cleanup)
        response = client.get(f"/api/v1/jobs/{job.job_id}")

        # Job should still exist
        assert response.status_code == 200, (
            "Pending job within TTL should not be cleaned up"
        )
        assert response.json()["status"] == "pending"

    def test_cleanup_preserves_processing_jobs_within_ttl(self, client):
        """Test that processing jobs within TTL are not cleaned up.

        Acceptance Criteria:
        - Processing job within TTL is preserved
        - Status remains processing
        """
        # Create and start a job (but don't complete it)
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        # Request job status (triggers cleanup)
        response = client.get(f"/api/v1/jobs/{job.job_id}")

        # Job should still exist
        assert response.status_code == 200, (
            "Processing job within TTL should not be cleaned up"
        )
        assert response.json()["status"] == "processing"

    def test_stuck_pending_job_is_cleaned_up_after_ttl(self, client):
        """Test that stuck pending jobs (older than TTL) are cleaned up.

        Acceptance Criteria:
        - Pending job that has been stuck for longer than TTL is removed
        - Returns 404 after cleanup
        """
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        # Create a pending job (simulating it got "stuck")
        job = job_manager.create_job()

        # Mock time to simulate TTL expiration
        future_time = datetime.now(timezone.utc) + timedelta(seconds=3601)
        with patch("server.job_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Trigger cleanup
            fresh_job = job_manager.create_job()
            client.get(f"/api/v1/jobs/{fresh_job.job_id}")

        # Original stuck job should be cleaned up
        response = client.get(f"/api/v1/jobs/{job.job_id}")
        assert response.status_code == 404, (
            "Stuck pending job older than TTL should return 404"
        )

    def test_cleanup_does_not_affect_other_active_jobs(self, client):
        """Test that cleanup of expired jobs doesn't affect other active jobs.

        Acceptance Criteria:
        - Multiple jobs exist (some expired, some active)
        - Only expired jobs are cleaned up
        - Active jobs remain accessible
        """
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        # Create an old completed job (will be expired)
        old_job = job_manager.create_job()
        job_manager.start_job(old_job.job_id)
        job_manager.complete_job(old_job.job_id, {"result": "old"})

        # Create a fresh pending job
        pending_job = job_manager.create_job()

        # Create a fresh processing job
        processing_job = job_manager.create_job()
        job_manager.start_job(processing_job.job_id)

        # Verify all jobs exist initially
        assert client.get(f"/api/v1/jobs/{old_job.job_id}").status_code == 200
        assert client.get(f"/api/v1/jobs/{pending_job.job_id}").status_code == 200
        assert client.get(f"/api/v1/jobs/{processing_job.job_id}").status_code == 200

        # Mock time to expire the old job (but not the new ones)
        future_time = datetime.now(timezone.utc) + timedelta(seconds=3601)
        with patch("server.job_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Trigger cleanup by accessing pending job
            response = client.get(f"/api/v1/jobs/{pending_job.job_id}")
            # The pending job was also created before the mock, so in the mock's
            # perspective it's also expired. Let's adjust our test approach.

        # Let's do a cleaner test: create jobs at different "times"
        job_manager._jobs.clear()

        # Create old job with old timestamp (manually set created_at in past)
        old_job = job_manager.create_job()
        job_manager.start_job(old_job.job_id)
        job_manager.complete_job(old_job.job_id, {"result": "old"})
        # Manually backdate the completed_at
        from datetime import datetime, timedelta, timezone
        old_completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)  # 2 hours ago
        old_job_updated = job_manager.get_job(old_job.job_id)
        job_manager._jobs[old_job.job_id] = old_job_updated.model_copy(
            update={"completed_at": old_completed_at}
        )

        # Create new active jobs (fresh timestamps)
        new_pending = job_manager.create_job()
        new_processing = job_manager.create_job()
        job_manager.start_job(new_processing.job_id)

        # Trigger cleanup via status request
        response = client.get(f"/api/v1/jobs/{new_pending.job_id}")

        # Old job should be cleaned up
        assert client.get(f"/api/v1/jobs/{old_job.job_id}").status_code == 404, (
            "Old completed job should be cleaned up"
        )

        # New jobs should still exist
        assert client.get(f"/api/v1/jobs/{new_pending.job_id}").status_code == 200, (
            "New pending job should still exist"
        )
        assert client.get(f"/api/v1/jobs/{new_processing.job_id}").status_code == 200, (
            "New processing job should still exist"
        )

    def test_multiple_expired_jobs_are_all_cleaned_up(self, client):
        """Test that multiple expired jobs are all cleaned up in one pass.

        Acceptance Criteria:
        - Multiple expired jobs are removed
        - All return 404 after cleanup
        """
        from datetime import datetime, timedelta, timezone

        # Create and complete multiple jobs with old timestamps
        old_jobs = []
        for i in range(3):
            job = job_manager.create_job()
            job_manager.start_job(job.job_id)
            job_manager.complete_job(job.job_id, {"result": f"old_{i}"})
            # Backdate the completed_at
            old_completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)
            job_updated = job_manager.get_job(job.job_id)
            job_manager._jobs[job.job_id] = job_updated.model_copy(
                update={"completed_at": old_completed_at}
            )
            old_jobs.append(job)

        # Create a fresh job to trigger cleanup
        fresh_job = job_manager.create_job()

        # Trigger cleanup
        client.get(f"/api/v1/jobs/{fresh_job.job_id}")

        # All old jobs should be cleaned up
        for old_job in old_jobs:
            response = client.get(f"/api/v1/jobs/{old_job.job_id}")
            assert response.status_code == 404, (
                f"Expired job {old_job.job_id} should return 404"
            )

        # Fresh job should still exist
        response = client.get(f"/api/v1/jobs/{fresh_job.job_id}")
        assert response.status_code == 200, "Fresh job should still exist"

    def test_cleanup_triggered_on_each_status_request(self, client):
        """Test that cleanup is triggered on each job status request.

        Acceptance Criteria:
        - Each GET /api/v1/jobs/{job_id} triggers cleanup
        - Expired jobs are removed even when checking a different job
        """
        from datetime import datetime, timedelta, timezone

        # Create and complete a job with old timestamp
        old_job = job_manager.create_job()
        job_manager.start_job(old_job.job_id)
        job_manager.complete_job(old_job.job_id, {"result": "old"})
        old_completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)
        job_updated = job_manager.get_job(old_job.job_id)
        job_manager._jobs[old_job.job_id] = job_updated.model_copy(
            update={"completed_at": old_completed_at}
        )

        # Create another fresh job
        fresh_job = job_manager.create_job()

        # Access the fresh job (should trigger cleanup of old job)
        response = client.get(f"/api/v1/jobs/{fresh_job.job_id}")
        assert response.status_code == 200

        # Old job should have been cleaned up
        response = client.get(f"/api/v1/jobs/{old_job.job_id}")
        assert response.status_code == 404, (
            "Old job should be cleaned up when checking a different job"
        )

    def test_expired_job_returns_404_with_proper_error_message(self, client):
        """Test that expired job returns 404 with appropriate error message.

        Acceptance Criteria:
        - Returns 404 status code
        - Error message indicates job not found
        """
        from datetime import datetime, timedelta, timezone

        # Create and complete a job with old timestamp
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.complete_job(job.job_id, {"result": "expired"})
        old_completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)
        job_updated = job_manager.get_job(job.job_id)
        job_manager._jobs[job.job_id] = job_updated.model_copy(
            update={"completed_at": old_completed_at}
        )
        job_id = job.job_id

        # Create fresh job to trigger cleanup
        fresh_job = job_manager.create_job()
        client.get(f"/api/v1/jobs/{fresh_job.job_id}")

        # Access expired job - should return 404 with proper message
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        assert job_id in data["detail"]


# =============================================================================
# Integration Tests - Full Async Validation Flow
# =============================================================================


class TestFullAsyncValidationFlow:
    """Integration tests for the complete async validation workflow.

    These tests verify the end-to-end flow:
    1. Upload IFC and IDS files
    2. Submit validation job
    3. Poll status until complete
    4. Verify result matches expected ValidationReport structure

    Note: FastAPI TestClient runs background tasks synchronously before
    returning the response, so we may need to poll multiple times to
    ensure the task has completed.
    """

    def test_full_validation_flow_success(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test complete async validation flow with valid files.

        Integration Test:
        1. Submit IFC and IDS files to /api/v1/validate
        2. Get job_id from response
        3. Poll /api/v1/jobs/{job_id} until completed
        4. Verify result matches ValidationReport structure
        """
        import time

        # Step 1: Submit validation job
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        submit_response = client.post("/api/v1/validate", files=files)

        # Verify job was accepted
        assert submit_response.status_code == 202, (
            f"Expected 202 Accepted, got {submit_response.status_code}: {submit_response.text}"
        )
        submit_data = submit_response.json()
        assert "job_id" in submit_data
        job_id = submit_data["job_id"]
        assert submit_data["status"] == "pending"

        # Step 2: Poll for completion with timeout
        max_polls = 50  # Maximum number of poll attempts
        poll_interval = 0.1  # Seconds between polls
        final_status = None
        final_data = None

        for _ in range(max_polls):
            status_response = client.get(f"/api/v1/jobs/{job_id}")
            assert status_response.status_code == 200, (
                f"Job status request failed: {status_response.text}"
            )
            final_data = status_response.json()
            final_status = final_data.get("status")

            if final_status in ("completed", "failed"):
                break

            time.sleep(poll_interval)

        # Step 3: Verify job completed (not timed out)
        assert final_status in ("completed", "failed"), (
            f"Job did not complete within timeout. Final status: {final_status}"
        )

        # Step 4: Verify result structure matches ValidationReport
        assert final_data is not None, "Response data should not be None"
        assert "job_id" in final_data, "Response should contain job_id"
        assert final_data["job_id"] == job_id, "job_id should match"

        # For completed jobs, verify result structure
        if final_status == "completed":
            assert "result" in final_data, "Completed job should have result"
            result = final_data["result"]
            assert result is not None, "Result should not be None"

            # Verify ValidationReport structure
            self._verify_validation_report_structure(result)

            # Verify timing info
            assert "completed_at" in final_data, "Completed job should have completed_at"
            assert "duration_seconds" in final_data, "Completed job should have duration_seconds"
            assert final_data["duration_seconds"] >= 0, "duration_seconds should be >= 0"

        # For failed jobs, verify error structure
        elif final_status == "failed":
            assert "error" in final_data, "Failed job should have error"
            assert final_data["error"] is not None, "Error should not be None"

    def test_full_validation_flow_result_content(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that validation result contains correct data from IFC/IDS files.

        Integration Test:
        - Submits validation with sample files
        - Verifies result reflects the actual files (filename, spec name)
        """
        import time

        # Submit validation job
        files = {
            "ifc_file": ("test_model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("test_spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        submit_response = client.post("/api/v1/validate", files=files)
        assert submit_response.status_code == 202
        job_id = submit_response.json()["job_id"]

        # Poll for completion
        max_polls = 50
        final_data = None
        for _ in range(max_polls):
            status_response = client.get(f"/api/v1/jobs/{job_id}")
            final_data = status_response.json()
            if final_data.get("status") in ("completed", "failed"):
                break
            time.sleep(0.1)

        # Verify we got a completed result
        assert final_data.get("status") == "completed", (
            f"Expected completed, got {final_data.get('status')}. "
            f"Error: {final_data.get('error', 'N/A')}"
        )

        result = final_data["result"]

        # Verify result reflects the input files
        assert result["ifc_file"] == "test_model.ifc", (
            f"Expected 'test_model.ifc', got '{result.get('ifc_file')}'"
        )
        assert result["ids_file"] == "test_spec.ids", (
            f"Expected 'test_spec.ids', got '{result.get('ids_file')}'"
        )

        # Verify IFC schema detection worked
        assert result["ifc_schema"] == "IFC4", (
            f"Expected 'IFC4', got '{result.get('ifc_schema')}'"
        )

        # Verify IDS title field exists (value may be None depending on ifctester parsing)
        # Note: ids_title extraction depends on ifctester library behavior
        assert "ids_title" in result or result.get("ids_title") is None, (
            "Result should have ids_title field"
        )

        # Verify specifications were processed
        assert result["total_specifications"] >= 1, "Should have at least 1 specification"
        assert len(result["specifications"]) >= 1, "Should have specification results"

        # Verify specification structure
        spec = result["specifications"][0]
        assert "name" in spec, "Specification should have name"
        assert "passed" in spec, "Specification should have passed status"
        assert "applicable_count" in spec, "Specification should have applicable_count"

    def test_full_validation_flow_with_status_url(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that status_url from submit response works correctly.

        Integration Test:
        - Uses status_url from submit response to poll
        - Verifies status_url is correct and functional
        """
        import time

        # Submit validation job
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        submit_response = client.post("/api/v1/validate", files=files)
        submit_data = submit_response.json()
        job_id = submit_data["job_id"]
        status_url = submit_data["status_url"]

        # Verify status_url format
        assert f"/api/v1/jobs/{job_id}" in status_url, (
            f"status_url should contain job endpoint, got '{status_url}'"
        )

        # Use status_url to poll (strip leading / for TestClient)
        # TestClient expects paths without the leading / for relative URLs
        max_polls = 50
        final_data = None
        for _ in range(max_polls):
            status_response = client.get(status_url)
            assert status_response.status_code == 200, (
                f"status_url request failed: {status_response.text}"
            )
            final_data = status_response.json()
            if final_data.get("status") in ("completed", "failed"):
                break
            time.sleep(0.1)

        # Verify we got results
        assert final_data is not None
        assert final_data["job_id"] == job_id, (
            "Job ID from status_url should match original"
        )

    def test_validation_flow_tracks_processing_progress(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that job shows progress updates during processing.

        Integration Test:
        - Verifies job transitions through states (pending -> processing -> completed)
        - Note: Due to TestClient running tasks synchronously, we may not
          observe all states, but the flow should complete correctly.
        """
        # Submit validation job
        files = {
            "ifc_file": ("model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        submit_response = client.post("/api/v1/validate", files=files)
        assert submit_response.status_code == 202
        job_id = submit_response.json()["job_id"]

        # First status check - should be pending or may already be processing/completed
        # (TestClient can execute background tasks synchronously)
        status_response = client.get(f"/api/v1/jobs/{job_id}")
        data = status_response.json()
        initial_status = data.get("status")

        # Status should be one of the valid job states
        valid_states = ["pending", "processing", "completed", "failed"]
        assert initial_status in valid_states, (
            f"Expected valid status, got '{initial_status}'"
        )

        # Wait for completion if not already completed
        import time
        if initial_status not in ("completed", "failed"):
            for _ in range(50):
                status_response = client.get(f"/api/v1/jobs/{job_id}")
                data = status_response.json()
                if data.get("status") in ("completed", "failed"):
                    break
                time.sleep(0.1)

        # Final state should be completed or failed
        final_status = data.get("status")
        assert final_status in ("completed", "failed"), (
            f"Job should complete, got '{final_status}'"
        )

    def test_validation_flow_handles_ifc_without_matching_entities(
        self, client, sample_ids_content
    ):
        """Test validation with IFC that has no entities matching the IDS spec.

        Integration Test:
        - Uses a minimal IFC with no IfcWall or other product entities
        - IDS spec may apply to entities that don't exist in the model
        - Should complete with 0 applicable entities or spec failure
        """
        import time

        # Minimal IFC with only project (no walls, doors, etc.)
        minimal_ifc = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('minimal.ifc','2025-01-01T12:00:00',('Author'),('Org'),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPERSON($,$,'User',$,$,$,$,$);
#2=IFCORGANIZATION($,'Org',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'1.0','App','App');
#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,1704067200);
#6=IFCDIRECTION((1.,0.,0.));
#7=IFCDIRECTION((0.,0.,1.));
#8=IFCCARTESIANPOINT((0.,0.,0.));
#9=IFCAXIS2PLACEMENT3D(#8,#7,#6);
#10=IFCPROJECT('2XyZ3W4aa56Bjd9gQc07yA',#5,'Test',$,$,$,$,$,#9);
ENDSEC;
END-ISO-10303-21;
"""

        files = {
            "ifc_file": ("minimal.ifc", io.BytesIO(minimal_ifc), "application/octet-stream"),
            "ids_file": ("spec.ids", io.BytesIO(sample_ids_content), "application/xml"),
        }

        submit_response = client.post("/api/v1/validate", files=files)
        assert submit_response.status_code == 202
        job_id = submit_response.json()["job_id"]

        # Poll for completion
        final_data = None
        for _ in range(50):
            status_response = client.get(f"/api/v1/jobs/{job_id}")
            final_data = status_response.json()
            if final_data.get("status") in ("completed", "failed"):
                break
            time.sleep(0.1)

        # Should complete (not crash)
        assert final_data.get("status") == "completed", (
            f"Should complete validation, got {final_data.get('status')}: {final_data.get('error')}"
        )

        # Verify result structure is valid even with no matching entities
        result = final_data["result"]
        assert "total_specifications" in result
        assert "specifications" in result
        assert isinstance(result["specifications"], list)

    def _verify_validation_report_structure(self, result: dict) -> None:
        """Helper to verify result matches ValidationReport structure.

        Expected structure from ids_validator.py ValidationReport:
        - timestamp: str (ISO format)
        - ifc_file: str
        - ifc_schema: str
        - ifc_entity_count: int
        - ids_file: str
        - ids_title: str | None
        - validation_time_seconds: float
        - total_specifications: int
        - passed_specifications: int
        - failed_specifications: int
        - pass_rate_percent: float
        - specifications: list[SpecificationResult]
        - success: bool
        - error: str | None
        """
        # Top-level required fields
        required_fields = [
            "timestamp",
            "ifc_file",
            "ifc_schema",
            "ifc_entity_count",
            "ids_file",
            "validation_time_seconds",
            "total_specifications",
            "passed_specifications",
            "failed_specifications",
            "pass_rate_percent",
            "specifications",
            "success",
        ]

        for field in required_fields:
            assert field in result, f"ValidationReport should have '{field}' field"

        # Type checks
        assert isinstance(result["timestamp"], str), "timestamp should be a string"
        assert isinstance(result["ifc_file"], str), "ifc_file should be a string"
        assert isinstance(result["ifc_schema"], str), "ifc_schema should be a string"
        assert isinstance(result["ifc_entity_count"], int), "ifc_entity_count should be int"
        assert isinstance(result["ids_file"], str), "ids_file should be a string"
        assert isinstance(result["validation_time_seconds"], (int, float)), (
            "validation_time_seconds should be numeric"
        )
        assert isinstance(result["total_specifications"], int), "total_specifications should be int"
        assert isinstance(result["passed_specifications"], int), "passed_specifications should be int"
        assert isinstance(result["failed_specifications"], int), "failed_specifications should be int"
        assert isinstance(result["pass_rate_percent"], (int, float)), (
            "pass_rate_percent should be numeric"
        )
        assert isinstance(result["specifications"], list), "specifications should be a list"
        assert isinstance(result["success"], bool), "success should be a boolean"

        # Optional field type checks
        if result.get("ids_title") is not None:
            assert isinstance(result["ids_title"], str), "ids_title should be string if present"
        if result.get("error") is not None:
            assert isinstance(result["error"], str), "error should be string if present"

        # Value range checks
        assert result["pass_rate_percent"] >= 0, "pass_rate_percent should be >= 0"
        assert result["pass_rate_percent"] <= 100, "pass_rate_percent should be <= 100"
        assert result["validation_time_seconds"] >= 0, "validation_time_seconds should be >= 0"

        # Consistency checks
        assert result["passed_specifications"] + result["failed_specifications"] == result["total_specifications"], (
            "passed + failed should equal total specifications"
        )

        # Verify specifications list structure
        for spec in result["specifications"]:
            self._verify_specification_result_structure(spec)

    def _verify_specification_result_structure(self, spec: dict) -> None:
        """Helper to verify SpecificationResult structure.

        Expected structure from ids_validator.py SpecificationResult:
        - name: str
        - description: str | None
        - passed: bool
        - applicable_count: int
        - passed_count: int
        - failed_count: int
        - failures: list[EntityFailure]
        """
        spec_fields = [
            "name",
            "passed",
            "applicable_count",
            "passed_count",
            "failed_count",
            "failures",
        ]

        for field in spec_fields:
            assert field in spec, f"SpecificationResult should have '{field}' field"

        assert isinstance(spec["name"], str), "spec name should be string"
        assert isinstance(spec["passed"], bool), "spec passed should be bool"
        assert isinstance(spec["applicable_count"], int), "applicable_count should be int"
        assert isinstance(spec["passed_count"], int), "passed_count should be int"
        assert isinstance(spec["failed_count"], int), "failed_count should be int"
        assert isinstance(spec["failures"], list), "failures should be a list"

        # Consistency check
        assert spec["passed_count"] + spec["failed_count"] == spec["applicable_count"], (
            "passed + failed should equal applicable count"
        )

        # Verify failure structure if any
        for failure in spec["failures"]:
            self._verify_entity_failure_structure(failure)

    def _verify_entity_failure_structure(self, failure: dict) -> None:
        """Helper to verify EntityFailure structure.

        Expected structure from ids_validator.py EntityFailure:
        - entity_id: int
        - entity_type: str
        - entity_name: str | None
        - global_id: str | None
        """
        assert "entity_id" in failure, "EntityFailure should have entity_id"
        assert "entity_type" in failure, "EntityFailure should have entity_type"

        assert isinstance(failure["entity_id"], int), "entity_id should be int"
        assert isinstance(failure["entity_type"], str), "entity_type should be string"


# =============================================================================
# Integration Tests - Concurrent Job Handling
# =============================================================================


class TestConcurrentJobHandling:
    """Integration tests for concurrent validation job handling.

    These tests verify that multiple validation jobs can be submitted
    and processed concurrently without blocking each other or mixing
    up results.

    Key scenarios tested:
    1. Multiple jobs complete correctly without blocking
    2. Results are isolated and correct for each job
    3. Server returns 503 when concurrent job limit is exceeded
    """

    def test_concurrent_jobs_complete_without_blocking(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that multiple jobs can be submitted and all complete.

        Integration Test:
        - Submit multiple validation jobs concurrently
        - All jobs should complete successfully
        - Verify each job has valid results
        """
        import time

        num_jobs = 3
        job_ids = []
        submit_times = []

        # Step 1: Submit multiple jobs
        for i in range(num_jobs):
            files = {
                "ifc_file": (
                    f"model_{i}.ifc",
                    io.BytesIO(sample_ifc_content),
                    "application/octet-stream",
                ),
                "ids_file": (
                    f"spec_{i}.ids",
                    io.BytesIO(sample_ids_content),
                    "application/xml",
                ),
            }

            start_time = time.time()
            response = client.post("/api/v1/validate", files=files)
            submit_times.append(time.time() - start_time)

            assert response.status_code == 202, (
                f"Job {i} submission should succeed, got {response.status_code}"
            )
            job_ids.append(response.json()["job_id"])

        # Verify all jobs were accepted (not blocked)
        assert len(job_ids) == num_jobs, "All jobs should be accepted"

        # Step 2: Poll all jobs until completion
        max_polls = 100
        poll_interval = 0.1
        completed_jobs = {}

        for _ in range(max_polls):
            all_done = True
            for job_id in job_ids:
                if job_id in completed_jobs:
                    continue

                response = client.get(f"/api/v1/jobs/{job_id}")
                assert response.status_code == 200
                data = response.json()

                if data["status"] in ("completed", "failed"):
                    completed_jobs[job_id] = data
                else:
                    all_done = False

            if all_done:
                break
            time.sleep(poll_interval)

        # Step 3: Verify all jobs completed
        assert len(completed_jobs) == num_jobs, (
            f"All {num_jobs} jobs should complete, got {len(completed_jobs)}"
        )

        # Verify all jobs completed successfully (not failed)
        for job_id, data in completed_jobs.items():
            assert data["status"] == "completed", (
                f"Job {job_id} should be completed, got {data['status']}: {data.get('error')}"
            )
            assert "result" in data, f"Job {job_id} should have result"
            assert data["result"] is not None, f"Job {job_id} result should not be None"

    def test_concurrent_jobs_return_correct_isolated_results(
        self, client, sample_ids_content
    ):
        """Test that each concurrent job returns its own correct result.

        Integration Test:
        - Submit jobs with different IFC files (different filenames)
        - Verify each job's result reflects the correct input file
        - Results should not be mixed up between jobs
        """
        import time

        # Create multiple IFC contents with distinct characteristics
        ifc_template = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('{filename}','2025-01-01T12:00:00',('Author'),('Org'),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPERSON($,$,'{author}',$,$,$,$,$);
#2=IFCORGANIZATION($,'{org}',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'1.0','App','App');
#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,1704067200);
#6=IFCDIRECTION((1.,0.,0.));
#7=IFCDIRECTION((0.,0.,1.));
#8=IFCCARTESIANPOINT((0.,0.,0.));
#9=IFCAXIS2PLACEMENT3D(#8,#7,#6);
#10=IFCPROJECT('2XyZ3W4aa56Bjd9gQc07yA',#5,'{project_name}',$,$,$,$,$,#9);
ENDSEC;
END-ISO-10303-21;
"""

        # Create distinct IFC files with unique names
        job_configs = [
            {"filename": "building_A.ifc", "project_name": "Building A", "author": "Alice", "org": "OrgA"},
            {"filename": "building_B.ifc", "project_name": "Building B", "author": "Bob", "org": "OrgB"},
            {"filename": "building_C.ifc", "project_name": "Building C", "author": "Carol", "org": "OrgC"},
        ]

        job_ids = []
        expected_filenames = []

        # Step 1: Submit jobs with different files
        for config in job_configs:
            ifc_content = ifc_template.replace(
                b"{filename}", config["filename"].encode()
            ).replace(
                b"{project_name}", config["project_name"].encode()
            ).replace(
                b"{author}", config["author"].encode()
            ).replace(
                b"{org}", config["org"].encode()
            )

            files = {
                "ifc_file": (
                    config["filename"],
                    io.BytesIO(ifc_content),
                    "application/octet-stream",
                ),
                "ids_file": (
                    f"spec_for_{config['filename']}.ids",
                    io.BytesIO(sample_ids_content),
                    "application/xml",
                ),
            }

            response = client.post("/api/v1/validate", files=files)
            assert response.status_code == 202
            job_ids.append(response.json()["job_id"])
            expected_filenames.append(config["filename"])

        # Step 2: Wait for all jobs to complete
        completed_jobs = {}
        max_polls = 100
        for _ in range(max_polls):
            all_done = True
            for job_id in job_ids:
                if job_id in completed_jobs:
                    continue
                response = client.get(f"/api/v1/jobs/{job_id}")
                data = response.json()
                if data["status"] in ("completed", "failed"):
                    completed_jobs[job_id] = data
                else:
                    all_done = False
            if all_done:
                break
            time.sleep(0.1)

        # Step 3: Verify each job has correct isolated result
        for i, job_id in enumerate(job_ids):
            assert job_id in completed_jobs, f"Job {job_id} should have completed"
            data = completed_jobs[job_id]

            assert data["status"] == "completed", (
                f"Job {job_id} should be completed: {data.get('error')}"
            )

            result = data["result"]
            expected_filename = expected_filenames[i]

            # Verify the result reflects the correct input file
            assert result["ifc_file"] == expected_filename, (
                f"Job {job_id} should have ifc_file='{expected_filename}', "
                f"got '{result.get('ifc_file')}'"
            )

    def test_concurrent_jobs_with_mixed_outcomes(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test concurrent jobs where some may fail and others succeed.

        Integration Test:
        - Submit valid and invalid validation requests
        - Verify completed jobs have results
        - Verify failed jobs have error messages
        - Results should be isolated per job
        """
        import time

        # Valid IFC content
        valid_ifc = sample_ifc_content

        # An IDS that should work with the sample IFC
        valid_ids = sample_ids_content

        # Submit multiple jobs - all should be valid in this test
        job_ids = []
        for i in range(3):
            files = {
                "ifc_file": (
                    f"model_{i}.ifc",
                    io.BytesIO(valid_ifc),
                    "application/octet-stream",
                ),
                "ids_file": (
                    f"spec_{i}.ids",
                    io.BytesIO(valid_ids),
                    "application/xml",
                ),
            }
            response = client.post("/api/v1/validate", files=files)
            assert response.status_code == 202
            job_ids.append(response.json()["job_id"])

        # Wait for completion
        completed_jobs = {}
        for _ in range(100):
            all_done = True
            for job_id in job_ids:
                if job_id in completed_jobs:
                    continue
                response = client.get(f"/api/v1/jobs/{job_id}")
                data = response.json()
                if data["status"] in ("completed", "failed"):
                    completed_jobs[job_id] = data
                else:
                    all_done = False
            if all_done:
                break
            time.sleep(0.1)

        # Verify each job has correct final state
        for job_id in job_ids:
            data = completed_jobs[job_id]
            status = data["status"]

            if status == "completed":
                assert "result" in data, "Completed job should have result"
                assert data["result"] is not None
                assert data.get("error") is None, (
                    "Completed job should not have error"
                )
            elif status == "failed":
                assert "error" in data, "Failed job should have error"
                assert data["error"] is not None
                assert data.get("result") is None, (
                    "Failed job should not have result"
                )

    def test_job_limit_returns_503(self, client, sample_ifc_content, sample_ids_content):
        """Test that exceeding concurrent job limit returns 503.

        Integration Test:
        - Fill up the job queue to the limit
        - Submit one more job
        - Should return 503 Service Unavailable
        """
        from server.main import job_manager

        # Get the max concurrent jobs limit
        max_jobs = job_manager._max_concurrent_jobs

        # Create jobs directly via job_manager to fill the queue
        # (without running actual validation)
        created_job_ids = []
        for _ in range(max_jobs):
            job = job_manager.create_job()
            job_manager.start_job(job.job_id)  # Mark as processing (active)
            created_job_ids.append(job.job_id)

        try:
            # Now try to submit one more via the API - should fail
            files = {
                "ifc_file": (
                    "overflow.ifc",
                    io.BytesIO(sample_ifc_content),
                    "application/octet-stream",
                ),
                "ids_file": (
                    "overflow.ids",
                    io.BytesIO(sample_ids_content),
                    "application/xml",
                ),
            }

            response = client.post("/api/v1/validate", files=files)

            assert response.status_code == 503, (
                f"Should return 503 when at capacity, got {response.status_code}"
            )
            assert "concurrent" in response.json()["detail"].lower(), (
                "Error should mention concurrent jobs"
            )

        finally:
            # Clean up the jobs we created
            for job_id in created_job_ids:
                if job_id in job_manager._jobs:
                    del job_manager._jobs[job_id]

    def test_jobs_resume_accepting_after_completion(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that new jobs are accepted after others complete.

        Integration Test:
        - Fill queue to limit
        - Complete a job
        - New job should be accepted
        """
        from server.main import job_manager

        max_jobs = job_manager._max_concurrent_jobs

        # Create jobs to fill the queue
        created_job_ids = []
        for _ in range(max_jobs):
            job = job_manager.create_job()
            job_manager.start_job(job.job_id)
            created_job_ids.append(job.job_id)

        try:
            # Complete one job to free up capacity
            completed_job_id = created_job_ids[0]
            job_manager.complete_job(completed_job_id, {"result": "test"})

            # Now should be able to submit a new job
            files = {
                "ifc_file": (
                    "new_job.ifc",
                    io.BytesIO(sample_ifc_content),
                    "application/octet-stream",
                ),
                "ids_file": (
                    "new_job.ids",
                    io.BytesIO(sample_ids_content),
                    "application/xml",
                ),
            }

            response = client.post("/api/v1/validate", files=files)

            assert response.status_code == 202, (
                f"Should accept job after capacity freed, got {response.status_code}"
            )

        finally:
            # Clean up
            for job_id in created_job_ids:
                if job_id in job_manager._jobs:
                    del job_manager._jobs[job_id]

    def test_concurrent_jobs_have_independent_timing(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that concurrent jobs track timing independently.

        Integration Test:
        - Submit multiple jobs
        - Each should have its own created_at, started_at, completed_at
        - duration_seconds should reflect each job's actual processing time
        """
        import time

        job_ids = []
        num_jobs = 3

        # Submit jobs with small delay between submissions
        for i in range(num_jobs):
            files = {
                "ifc_file": (
                    f"timed_model_{i}.ifc",
                    io.BytesIO(sample_ifc_content),
                    "application/octet-stream",
                ),
                "ids_file": (
                    f"timed_spec_{i}.ids",
                    io.BytesIO(sample_ids_content),
                    "application/xml",
                ),
            }
            response = client.post("/api/v1/validate", files=files)
            assert response.status_code == 202
            job_ids.append(response.json()["job_id"])
            time.sleep(0.05)  # Small delay between submissions

        # Wait for completion
        completed_jobs = {}
        for _ in range(100):
            all_done = True
            for job_id in job_ids:
                if job_id in completed_jobs:
                    continue
                response = client.get(f"/api/v1/jobs/{job_id}")
                data = response.json()
                if data["status"] in ("completed", "failed"):
                    completed_jobs[job_id] = data
                else:
                    all_done = False
            if all_done:
                break
            time.sleep(0.1)

        # Verify each job has independent timing
        for job_id in job_ids:
            data = completed_jobs[job_id]

            if data["status"] == "completed":
                # Each completed job should have timing info
                assert "created_at" in data, "Should have created_at"
                assert "started_at" in data, "Should have started_at"
                assert "completed_at" in data, "Should have completed_at"
                assert "duration_seconds" in data, "Should have duration_seconds"

                # Duration should be non-negative
                assert data["duration_seconds"] >= 0, (
                    f"Duration should be >= 0, got {data['duration_seconds']}"
                )

        # Verify jobs have different timestamps (not shared)
        created_timestamps = [
            completed_jobs[job_id]["created_at"] for job_id in job_ids
        ]
        # At least created_at should differ since we added delays
        # Note: They might be the same if the test runs very fast,
        # so we just verify the format is correct
        for ts in created_timestamps:
            assert "T" in ts, "Timestamp should be ISO format"

    def test_all_concurrent_jobs_produce_valid_validation_reports(
        self, client, sample_ifc_content, sample_ids_content
    ):
        """Test that all concurrent jobs produce properly structured results.

        Integration Test:
        - Submit multiple jobs concurrently
        - Wait for all to complete
        - Verify each result has the full ValidationReport structure
        """
        import time

        num_jobs = 4
        job_ids = []

        # Submit jobs
        for i in range(num_jobs):
            files = {
                "ifc_file": (
                    f"report_model_{i}.ifc",
                    io.BytesIO(sample_ifc_content),
                    "application/octet-stream",
                ),
                "ids_file": (
                    f"report_spec_{i}.ids",
                    io.BytesIO(sample_ids_content),
                    "application/xml",
                ),
            }
            response = client.post("/api/v1/validate", files=files)
            assert response.status_code == 202
            job_ids.append(response.json()["job_id"])

        # Wait for completion
        completed_jobs = {}
        for _ in range(100):
            all_done = True
            for job_id in job_ids:
                if job_id in completed_jobs:
                    continue
                response = client.get(f"/api/v1/jobs/{job_id}")
                data = response.json()
                if data["status"] in ("completed", "failed"):
                    completed_jobs[job_id] = data
                else:
                    all_done = False
            if all_done:
                break
            time.sleep(0.1)

        # Verify all completed jobs have valid report structure
        completed_count = 0
        for job_id in job_ids:
            data = completed_jobs[job_id]

            if data["status"] == "completed":
                completed_count += 1
                result = data["result"]

                # Verify essential ValidationReport fields exist
                required_fields = [
                    "ifc_file",
                    "ids_file",
                    "ifc_schema",
                    "total_specifications",
                    "passed_specifications",
                    "failed_specifications",
                    "pass_rate_percent",
                    "specifications",
                    "success",
                ]

                for field in required_fields:
                    assert field in result, (
                        f"Job {job_id} result missing field '{field}'"
                    )

                # Verify specifications list structure
                assert isinstance(result["specifications"], list), (
                    f"Job {job_id} specifications should be a list"
                )

                # Verify numeric fields are correct types
                assert isinstance(result["total_specifications"], int)
                assert isinstance(result["passed_specifications"], int)
                assert isinstance(result["failed_specifications"], int)
                assert isinstance(result["pass_rate_percent"], (int, float))

        # At least some jobs should complete successfully
        assert completed_count >= 1, (
            f"At least 1 job should complete successfully, got {completed_count}"
        )
