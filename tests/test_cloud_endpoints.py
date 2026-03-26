"""
Integration tests for the cloud storage API endpoints.

Tests both the 503 behavior (when not configured) and the endpoint
responses when the NextcloudClient is mocked.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_without_cloud():
    """Create a test app with cloud storage disabled."""
    with patch.dict(
        "os.environ",
        {
            "NEXTCLOUD_URL": "",
            "NEXTCLOUD_SERVICE_USER": "",
            "NEXTCLOUD_SERVICE_PASS": "",
        },
    ):
        # Force reimport to pick up env vars
        import importlib
        import server.main as main_module

        importlib.reload(main_module)
        yield main_module.app


@pytest.fixture
def client_without_cloud(app_without_cloud):
    """TestClient for app without cloud configured."""
    return TestClient(app_without_cloud)


class TestCloudNotConfigured:
    """Tests for when cloud storage is not configured (env vars empty)."""

    def test_status_returns_disabled(self, client_without_cloud):
        """GET /api/cloud/status returns enabled=false."""
        resp = client_without_cloud.get("/api/cloud/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["connected"] is False

    def test_projects_returns_503(self, client_without_cloud):
        """GET /api/cloud/projects returns 503 when not configured."""
        resp = client_without_cloud.get("/api/cloud/projects")
        assert resp.status_code == 503

    def test_files_returns_503(self, client_without_cloud):
        """GET /api/cloud/projects/test/files returns 503."""
        resp = client_without_cloud.get("/api/cloud/projects/test/files")
        assert resp.status_code == 503

    def test_download_returns_503(self, client_without_cloud):
        """GET /api/cloud/projects/test/files/report.bcf returns 503."""
        resp = client_without_cloud.get("/api/cloud/projects/test/files/report.bcf")
        assert resp.status_code == 503

    def test_delete_returns_503(self, client_without_cloud):
        """DELETE /api/cloud/projects/test/files/report.bcf returns 503."""
        resp = client_without_cloud.delete("/api/cloud/projects/test/files/report.bcf")
        assert resp.status_code == 503


class TestCloudConfigured:
    """Tests for when cloud storage is configured (mocked client)."""

    @pytest.fixture(autouse=True)
    def setup_mock(self):
        """Patch the nextcloud client in main module."""
        from server.nextcloud_client import DavItem

        self.mock_client = AsyncMock()
        self.mock_client.test_connection.return_value = True
        self.mock_client.list_projects.return_value = [
            DavItem(
                name="Project A",
                href="/Projects/Project%20A/",
                is_collection=True,
                content_length=0,
                last_modified="Mon, 01 Jan 2026 12:00:00 GMT",
            ),
        ]
        self.mock_client.list_files.return_value = [
            DavItem(
                name="report.bcf",
                href="/bim-validator/report.bcf",
                is_collection=False,
                content_length=5678,
                last_modified="Thu, 10 Mar 2026 09:15:00 GMT",
            ),
        ]
        self.mock_client.download_file.return_value = b"BCF_CONTENT"
        self.mock_client.upload_file.return_value = None
        self.mock_client.delete_file.return_value = None

        with patch.dict(
            "os.environ",
            {
                "NEXTCLOUD_URL": "https://cloud.test.com",
                "NEXTCLOUD_SERVICE_USER": "testuser",
                "NEXTCLOUD_SERVICE_PASS": "testpass",
            },
        ):
            import importlib
            import server.main as main_module

            importlib.reload(main_module)

            # Replace the global client
            main_module._nextcloud_client = self.mock_client
            main_module.CLOUD_ENABLED = True

            self.client = TestClient(main_module.app)
            yield
            main_module._nextcloud_client = None

    def test_status_enabled(self):
        """GET /api/cloud/status returns enabled=true, connected=true."""
        resp = self.client.get("/api/cloud/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["connected"] is True

    def test_list_projects(self):
        """GET /api/cloud/projects returns project list."""
        resp = self.client.get("/api/cloud/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "Project A"

    def test_list_files(self):
        """GET /api/cloud/projects/test/files returns file list."""
        resp = self.client.get("/api/cloud/projects/Project%20A/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"] == "Project A"
        assert len(data["files"]) == 1
        assert data["files"][0]["name"] == "report.bcf"
        assert data["files"][0]["size"] == 5678

    def test_download_file(self):
        """GET /api/cloud/projects/test/files/report.bcf returns file content."""
        resp = self.client.get("/api/cloud/projects/Project%20A/files/report.bcf")
        assert resp.status_code == 200
        assert resp.content == b"BCF_CONTENT"

    def test_delete_file(self):
        """DELETE /api/cloud/projects/test/files/report.bcf succeeds."""
        resp = self.client.delete("/api/cloud/projects/Project%20A/files/report.bcf")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
