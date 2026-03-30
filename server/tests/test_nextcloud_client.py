"""
Tests for NextcloudClient — project container model migration.

Tests cover:
- New path constants
- Fallback from new to legacy paths
- Manifest CRUD operations
- list_models / list_validation_files with fallback
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from server.nextcloud_client import (
    DIR_MODELS,
    DIR_VALIDATION,
    LEGACY_BIM_SUBDIR,
    LEGACY_OUTPUT_SUBDIR,
    MANIFEST_FILENAME,
    PROJECTS_ROOT,
    NextcloudClient,
    NextcloudError,
)


@pytest.fixture
def nc_client() -> NextcloudClient:
    """Create a NextcloudClient for testing."""
    return NextcloudClient(
        base_url="http://localhost:8080",
        username="testuser",
        password="testpass",
    )


# ── Constants ──────────────────────────────────────────────────


class TestConstants:
    """Verify new path constants are defined correctly."""

    def test_dir_models(self) -> None:
        assert DIR_MODELS == "models"

    def test_dir_validation(self) -> None:
        assert DIR_VALIDATION == "validation"

    def test_manifest_filename(self) -> None:
        assert MANIFEST_FILENAME == "project.wefc"

    def test_legacy_bim_subdir(self) -> None:
        assert LEGACY_BIM_SUBDIR == "70_BIM"

    def test_legacy_output_subdir(self) -> None:
        assert LEGACY_OUTPUT_SUBDIR == "99_overige_documenten/bim-validator"


# ── _tool_path now points to validation/ ─────────────────────


class TestToolPath:
    """Verify _tool_path uses the new validation/ directory."""

    def test_tool_path_uses_new_dir(self, nc_client: NextcloudClient) -> None:
        path = nc_client._tool_path("TestProject")
        assert path == f"{PROJECTS_ROOT}/TestProject/{DIR_VALIDATION}"
        assert "99_overige_documenten" not in path

    def test_legacy_tool_path(self, nc_client: NextcloudClient) -> None:
        path = nc_client._legacy_tool_path("TestProject")
        assert "99_overige_documenten/bim-validator" in path


# ── list_models fallback ─────────────────────────────────────


class TestListModels:
    """Test list_models with new-path-first, legacy fallback."""

    @pytest.mark.asyncio
    async def test_returns_new_path_files(
        self, nc_client: NextcloudClient
    ) -> None:
        """When models/ has files, return those."""
        mock_items = [MagicMock(is_collection=False, name="model.ifc")]
        with patch.object(
            nc_client, "list_files_at", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = mock_items
            result = await nc_client.list_models("Proj")
            mock_list.assert_called_once_with("Proj", DIR_MODELS)
            assert result == mock_items

    @pytest.mark.asyncio
    async def test_falls_back_to_legacy(
        self, nc_client: NextcloudClient
    ) -> None:
        """When models/ is empty, fall back to 70_BIM/."""
        legacy_items = [MagicMock(is_collection=False, name="old.ifc")]
        with patch.object(
            nc_client, "list_files_at", new_callable=AsyncMock
        ) as mock_list:
            mock_list.side_effect = [[], legacy_items]
            result = await nc_client.list_models("Proj")
            assert mock_list.call_count == 2
            assert mock_list.call_args_list[1][0] == (
                "Proj",
                LEGACY_BIM_SUBDIR,
            )
            assert result == legacy_items


# ── list_validation_files fallback ───────────────────────────


class TestListValidationFiles:
    """Test list_validation_files with fallback."""

    @pytest.mark.asyncio
    async def test_returns_new_path_files(
        self, nc_client: NextcloudClient
    ) -> None:
        mock_items = [MagicMock(is_collection=False)]
        with patch.object(
            nc_client, "list_files_at", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = mock_items
            result = await nc_client.list_validation_files("Proj")
            mock_list.assert_called_once_with("Proj", DIR_VALIDATION)
            assert result == mock_items

    @pytest.mark.asyncio
    async def test_falls_back_to_legacy(
        self, nc_client: NextcloudClient
    ) -> None:
        legacy_items = [MagicMock(is_collection=False)]
        with patch.object(
            nc_client, "list_files_at", new_callable=AsyncMock
        ) as mock_list:
            mock_list.side_effect = [[], legacy_items]
            result = await nc_client.list_validation_files("Proj")
            assert mock_list.call_count == 2
            assert mock_list.call_args_list[1][0] == (
                "Proj",
                LEGACY_OUTPUT_SUBDIR,
            )


# ── download_file fallback ───────────────────────────────────


class TestDownloadFileFallback:
    """Test download_file tries new path then legacy."""

    @pytest.mark.asyncio
    async def test_downloads_from_new_path(
        self, nc_client: NextcloudClient
    ) -> None:
        with patch.object(
            nc_client, "download_from", new_callable=AsyncMock
        ) as mock_dl:
            mock_dl.return_value = b"content"
            result = await nc_client.download_file("Proj", "test.json")
            mock_dl.assert_called_once_with(
                "Proj", "test.json", DIR_VALIDATION
            )
            assert result == b"content"

    @pytest.mark.asyncio
    async def test_falls_back_on_404(
        self, nc_client: NextcloudClient
    ) -> None:
        with patch.object(
            nc_client, "download_from", new_callable=AsyncMock
        ) as mock_dl:
            mock_dl.side_effect = [
                NextcloudError("Not found", status_code=404),
                b"legacy content",
            ]
            result = await nc_client.download_file("Proj", "test.json")
            assert mock_dl.call_count == 2
            assert result == b"legacy content"


# ── Manifest operations ──────────────────────────────────────


class TestManifestOperations:
    """Test manifest read/write/upsert."""

    @pytest.mark.asyncio
    async def test_read_manifest_returns_none_on_404(
        self, nc_client: NextcloudClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        nc_client._client = AsyncMock()
        nc_client._client.get = AsyncMock(return_value=mock_resp)
        result = await nc_client.read_manifest("Proj")
        assert result is None

    @pytest.mark.asyncio
    async def test_read_manifest_parses_json(
        self, nc_client: NextcloudClient
    ) -> None:
        manifest = {"header": {"schema": "WeFC"}, "data": []}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = json.dumps(manifest).encode()
        nc_client._client = AsyncMock()
        nc_client._client.get = AsyncMock(return_value=mock_resp)
        result = await nc_client.read_manifest("Proj")
        assert result == manifest

    @pytest.mark.asyncio
    async def test_write_manifest(
        self, nc_client: NextcloudClient
    ) -> None:
        manifest = {"header": {"schema": "WeFC"}, "data": []}
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        nc_client._client = AsyncMock()
        nc_client._client.put = AsyncMock(return_value=mock_resp)
        # Should not raise
        await nc_client.write_manifest("Proj", manifest)
        nc_client._client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_creates_manifest_if_missing(
        self, nc_client: NextcloudClient
    ) -> None:
        obj = {
            "type": "WefcValidation",
            "guid": "test-guid-123",
            "name": "Test",
        }
        with (
            patch.object(
                nc_client,
                "read_manifest",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                nc_client,
                "write_manifest",
                new_callable=AsyncMock,
            ) as mock_write,
        ):
            result = await nc_client.upsert_manifest_object(
                "Proj", obj
            )
            assert result["header"]["schema"] == "WeFC"
            assert len(result["data"]) == 1
            assert result["data"][0]["guid"] == "test-guid-123"
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_replaces_existing_by_guid(
        self, nc_client: NextcloudClient
    ) -> None:
        existing_manifest = {
            "header": {
                "schema": "WeFC",
                "schema_version": "1.0.0",
                "timestamp": "2026-01-01T00:00:00",
                "application": "test",
            },
            "data": [
                {
                    "type": "WefcValidation",
                    "guid": "guid-1",
                    "name": "Old",
                },
            ],
        }
        updated_obj = {
            "type": "WefcValidation",
            "guid": "guid-1",
            "name": "Updated",
        }
        with (
            patch.object(
                nc_client,
                "read_manifest",
                new_callable=AsyncMock,
                return_value=existing_manifest,
            ),
            patch.object(
                nc_client,
                "write_manifest",
                new_callable=AsyncMock,
            ),
        ):
            result = await nc_client.upsert_manifest_object(
                "Proj", updated_obj
            )
            assert len(result["data"]) == 1
            assert result["data"][0]["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_upsert_appends_new_object(
        self, nc_client: NextcloudClient
    ) -> None:
        existing_manifest = {
            "header": {
                "schema": "WeFC",
                "schema_version": "1.0.0",
                "timestamp": "2026-01-01T00:00:00",
                "application": "test",
            },
            "data": [
                {
                    "type": "WefcValidation",
                    "guid": "guid-1",
                    "name": "First",
                },
            ],
        }
        new_obj = {
            "type": "WefcValidation",
            "guid": "guid-2",
            "name": "Second",
        }
        with (
            patch.object(
                nc_client,
                "read_manifest",
                new_callable=AsyncMock,
                return_value=existing_manifest,
            ),
            patch.object(
                nc_client,
                "write_manifest",
                new_callable=AsyncMock,
            ),
        ):
            result = await nc_client.upsert_manifest_object(
                "Proj", new_obj
            )
            assert len(result["data"]) == 2
