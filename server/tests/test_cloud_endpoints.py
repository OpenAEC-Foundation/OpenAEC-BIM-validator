"""
Tests for cloud storage API endpoints.

Tests cover:
- Manifest endpoint (GET /api/cloud/projects/{project}/manifest)
- Validation upload with manifest update
- File listing with new category routing
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server.nextcloud_client import DIR_MODELS, DIR_VALIDATION


@pytest.fixture
def _mock_tenant():
    """Mock tenant resolution for all cloud endpoint tests."""
    mock_config = MagicMock()
    mock_config.slug = "3bm"
    mock_config.has_volume_mount = False

    mock_registry = MagicMock()
    mock_registry.is_configured = True
    mock_registry.get.return_value = mock_config

    with patch(
        "server.routers.cloud.get_tenants",
        return_value=mock_registry,
    ):
        yield mock_config


@pytest.fixture
def _mock_volume_unavailable():
    """Mock VolumeReader as unavailable (no volume mount)."""
    mock_reader = MagicMock()
    mock_reader.available = False

    with patch(
        "server.routers.cloud.VolumeReader",
        return_value=mock_reader,
    ):
        yield mock_reader


@pytest.fixture
def _mock_volume_available():
    """Mock VolumeReader as available (volume mount present)."""
    mock_reader = MagicMock()
    mock_reader.available = True

    with patch(
        "server.routers.cloud.VolumeReader",
        return_value=mock_reader,
    ):
        yield mock_reader


class TestManifestEndpoint:
    """Tests for GET /api/cloud/projects/{project}/manifest."""

    def test_manifest_not_found(
        self,
        client: TestClient,
        _mock_tenant: MagicMock,
        _mock_volume_unavailable: MagicMock,
    ) -> None:
        """Returns 404 when no manifest exists."""
        mock_nc = AsyncMock()
        mock_nc.read_manifest = AsyncMock(return_value=None)

        with patch(
            "server.routers.cloud.get_nc_client",
            return_value=mock_nc,
        ):
            resp = client.get("/api/cloud/projects/TestProj/manifest")
            assert resp.status_code == 404

    def test_manifest_from_webdav(
        self,
        client: TestClient,
        _mock_tenant: MagicMock,
        _mock_volume_unavailable: MagicMock,
    ) -> None:
        """Returns manifest JSON from WebDAV."""
        manifest = {
            "header": {
                "schema": "WeFC",
                "schema_version": "1.0.0",
                "timestamp": "2026-03-30T12:00:00",
                "application": "bim-validator",
            },
            "data": [
                {
                    "type": "WefcValidation",
                    "guid": "abc-123",
                    "name": "Test",
                }
            ],
        }
        mock_nc = AsyncMock()
        mock_nc.read_manifest = AsyncMock(return_value=manifest)

        with patch(
            "server.routers.cloud.get_nc_client",
            return_value=mock_nc,
        ):
            resp = client.get("/api/cloud/projects/TestProj/manifest")
            assert resp.status_code == 200
            body = resp.json()
            assert body["header"]["schema"] == "WeFC"
            assert len(body["data"]) == 1

    def test_manifest_from_volume_mount(
        self,
        client: TestClient,
        _mock_tenant: MagicMock,
        _mock_volume_available: MagicMock,
    ) -> None:
        """Returns manifest from volume mount when available."""
        manifest = {
            "header": {"schema": "WeFC"},
            "data": [],
        }
        _mock_volume_available.read_manifest.return_value = manifest

        resp = client.get("/api/cloud/projects/TestProj/manifest")
        assert resp.status_code == 200
        body = resp.json()
        assert body["header"]["schema"] == "WeFC"


class TestFileListingCategories:
    """Tests that category param routes to correct directories."""

    def test_bim_category_uses_models_dir(
        self,
        client: TestClient,
        _mock_tenant: MagicMock,
        _mock_volume_unavailable: MagicMock,
    ) -> None:
        """category=bim should call list_models (models/ + fallback)."""
        mock_nc = AsyncMock()
        mock_nc.list_models = AsyncMock(return_value=[])

        with patch(
            "server.routers.cloud.get_nc_client",
            return_value=mock_nc,
        ):
            resp = client.get(
                "/api/cloud/projects/TestProj/files?category=bim"
            )
            assert resp.status_code == 200
            mock_nc.list_models.assert_called_once_with("TestProj")

    def test_output_category_uses_validation_dir(
        self,
        client: TestClient,
        _mock_tenant: MagicMock,
        _mock_volume_unavailable: MagicMock,
    ) -> None:
        """category=output should call list_validation_files."""
        mock_nc = AsyncMock()
        mock_nc.list_validation_files = AsyncMock(return_value=[])

        with patch(
            "server.routers.cloud.get_nc_client",
            return_value=mock_nc,
        ):
            resp = client.get(
                "/api/cloud/projects/TestProj/files?category=output"
            )
            assert resp.status_code == 200
            mock_nc.list_validation_files.assert_called_once_with(
                "TestProj"
            )


class TestVolumeReaderFallback:
    """Test volume reader uses new paths with fallback."""

    def test_bim_listing_with_volume_mount(
        self,
        client: TestClient,
        _mock_tenant: MagicMock,
        _mock_volume_available: MagicMock,
    ) -> None:
        """Volume mount bim listing calls list_bim_files."""
        _mock_volume_available.list_bim_files.return_value = []

        resp = client.get(
            "/api/cloud/projects/TestProj/files?category=bim"
        )
        assert resp.status_code == 200
        _mock_volume_available.list_bim_files.assert_called_once_with(
            "TestProj"
        )

    def test_output_listing_with_volume_mount(
        self,
        client: TestClient,
        _mock_tenant: MagicMock,
        _mock_volume_available: MagicMock,
    ) -> None:
        """Volume mount output listing calls list_output_files."""
        _mock_volume_available.list_output_files.return_value = []

        resp = client.get(
            "/api/cloud/projects/TestProj/files?category=output"
        )
        assert resp.status_code == 200
        _mock_volume_available.list_output_files.assert_called_once_with(
            "TestProj"
        )
