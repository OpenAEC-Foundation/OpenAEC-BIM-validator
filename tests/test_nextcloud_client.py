"""
Unit tests for the Nextcloud WebDAV client.

Mocks httpx responses for PROPFIND, GET, PUT, DELETE, MKCOL operations.
"""

import pytest
import httpx

from server.nextcloud_client import NextcloudClient, NextcloudError


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def client():
    """Create a NextcloudClient instance for testing."""
    return NextcloudClient(
        base_url="https://cloud.example.com",
        username="testuser",
        password="testpass",
    )


# ── Sample XML responses ────────────────────────────────────────

PROPFIND_PROJECTS_XML = b"""<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/remote.php/dav/files/testuser/Projects/</d:href>
    <d:propstat>
      <d:prop>
        <d:resourcetype><d:collection/></d:resourcetype>
        <d:getcontentlength/>
        <d:getlastmodified>Mon, 01 Jan 2026 12:00:00 GMT</d:getlastmodified>
        <d:displayname>Projects</d:displayname>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/testuser/Projects/Project%20Alpha/</d:href>
    <d:propstat>
      <d:prop>
        <d:resourcetype><d:collection/></d:resourcetype>
        <d:getcontentlength/>
        <d:getlastmodified>Tue, 15 Jan 2026 10:30:00 GMT</d:getlastmodified>
        <d:displayname>Project Alpha</d:displayname>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/testuser/Projects/Project%20Beta/</d:href>
    <d:propstat>
      <d:prop>
        <d:resourcetype><d:collection/></d:resourcetype>
        <d:getcontentlength/>
        <d:getlastmodified>Wed, 20 Feb 2026 14:00:00 GMT</d:getlastmodified>
        <d:displayname>Project Beta</d:displayname>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""

PROPFIND_FILES_XML = b"""<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/remote.php/dav/files/testuser/Projects/Project%20Alpha/99_overige_documenten/bim-validator/</d:href>
    <d:propstat>
      <d:prop>
        <d:resourcetype><d:collection/></d:resourcetype>
        <d:getcontentlength/>
        <d:getlastmodified>Mon, 01 Jan 2026 12:00:00 GMT</d:getlastmodified>
        <d:displayname>bim-validator</d:displayname>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/testuser/Projects/Project%20Alpha/99_overige_documenten/bim-validator/report.bcf</d:href>
    <d:propstat>
      <d:prop>
        <d:resourcetype/>
        <d:getcontentlength>12345</d:getcontentlength>
        <d:getlastmodified>Thu, 10 Mar 2026 09:15:00 GMT</d:getlastmodified>
        <d:displayname>report.bcf</d:displayname>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""

PROPFIND_EMPTY_XML = b"""<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/remote.php/dav/files/testuser/Projects/Project%20Alpha/99_overige_documenten/bim-validator/</d:href>
    <d:propstat>
      <d:prop>
        <d:resourcetype><d:collection/></d:resourcetype>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""


# ── Synchronous tests (no I/O) ─────────────────────────────────


class TestNextcloudClientSync:
    """Synchronous tests for URL/path construction and XML parsing."""

    def test_webdav_root_url(self, client: NextcloudClient):
        """WebDAV root URL is correctly constructed."""
        expected = "https://cloud.example.com/remote.php/dav/files/testuser"
        assert client._webdav_root == expected

    def test_tool_path(self, client: NextcloudClient):
        """Tool path is correctly constructed for a project."""
        path = client._tool_path("My Project")
        assert path == "Projects/My%20Project/99_overige_documenten/bim-validator"

    def test_tool_path_special_chars(self, client: NextcloudClient):
        """Tool path correctly encodes special characters."""
        path = client._tool_path("Project & Test (2026)")
        assert "Project%20%26%20Test%20%282026%29" in path

    def test_parse_projects(self, client: NextcloudClient):
        """PROPFIND XML for projects is correctly parsed."""
        items = client._parse_multistatus(PROPFIND_PROJECTS_XML, "Projects/")
        assert len(items) == 2
        assert items[0].name == "Project Alpha"
        assert items[0].is_collection is True
        assert items[1].name == "Project Beta"

    def test_parse_files(self, client: NextcloudClient):
        """PROPFIND XML for files is correctly parsed."""
        path = "Projects/Project%20Alpha/99_overige_documenten/bim-validator/"
        items = client._parse_multistatus(PROPFIND_FILES_XML, path)
        assert len(items) == 1
        assert items[0].name == "report.bcf"
        assert items[0].is_collection is False
        assert items[0].content_length == 12345

    def test_parse_empty_directory(self, client: NextcloudClient):
        """PROPFIND XML for empty directory returns empty list."""
        path = "Projects/Project%20Alpha/99_overige_documenten/bim-validator/"
        items = client._parse_multistatus(PROPFIND_EMPTY_XML, path)
        assert len(items) == 0


# ── Async tests (mock I/O) ─────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
class TestNextcloudClientAsync:
    """Async tests for methods that perform HTTP I/O."""

    async def test_list_projects(self, client: NextcloudClient, monkeypatch):
        """list_projects() returns only collections."""
        async def mock_propfind(path, depth="1"):
            return httpx.Response(207, content=PROPFIND_PROJECTS_XML)

        monkeypatch.setattr(client, "_propfind", mock_propfind)
        projects = await client.list_projects()
        assert len(projects) == 2
        assert all(p.is_collection for p in projects)

    async def test_list_files(self, client: NextcloudClient, monkeypatch):
        """list_files() returns only non-collection items."""
        async def mock_propfind(path, depth="1"):
            return httpx.Response(207, content=PROPFIND_FILES_XML)

        monkeypatch.setattr(client, "_propfind", mock_propfind)
        files = await client.list_files("Project Alpha")
        assert len(files) == 1
        assert files[0].name == "report.bcf"

    async def test_list_files_404_returns_empty(
        self, client: NextcloudClient, monkeypatch
    ):
        """list_files() returns empty list when directory doesn't exist."""
        async def mock_propfind(path, depth="1"):
            raise NextcloudError("Not found", status_code=404)

        monkeypatch.setattr(client, "_propfind", mock_propfind)
        files = await client.list_files("Nonexistent")
        assert files == []

    async def test_download_file(self, client: NextcloudClient, monkeypatch):
        """download_file() returns raw bytes."""
        test_content = b"BCF file content here"

        async def mock_get(url, **kwargs):
            return httpx.Response(200, content=test_content)

        monkeypatch.setattr(client._client, "get", mock_get)
        content = await client.download_file("Project Alpha", "report.bcf")
        assert content == test_content

    async def test_download_file_404(self, client: NextcloudClient, monkeypatch):
        """download_file() raises NextcloudError for missing files."""
        async def mock_get(url, **kwargs):
            return httpx.Response(404)

        monkeypatch.setattr(client._client, "get", mock_get)
        with pytest.raises(NextcloudError) as exc_info:
            await client.download_file("Project Alpha", "missing.bcf")
        assert exc_info.value.status_code == 404

    async def test_upload_file(self, client: NextcloudClient, monkeypatch):
        """upload_file() sends PUT request with content."""
        put_calls: list[dict] = []

        async def mock_put(url, content=None, **kwargs):
            put_calls.append({"url": url, "content": content})
            return httpx.Response(201)

        async def mock_ensure_dir(path):
            pass

        monkeypatch.setattr(client._client, "put", mock_put)
        monkeypatch.setattr(client, "ensure_directory", mock_ensure_dir)

        await client.upload_file("Project Alpha", "new.bcf", b"bcf-data")
        assert len(put_calls) == 1
        assert put_calls[0]["content"] == b"bcf-data"
        assert "new.bcf" in put_calls[0]["url"]

    async def test_delete_file(self, client: NextcloudClient, monkeypatch):
        """delete_file() sends DELETE request."""
        async def mock_delete(url, **kwargs):
            return httpx.Response(204)

        monkeypatch.setattr(client._client, "delete", mock_delete)
        await client.delete_file("Project Alpha", "old.bcf")

    async def test_delete_file_404(self, client: NextcloudClient, monkeypatch):
        """delete_file() raises NextcloudError for missing files."""
        async def mock_delete(url, **kwargs):
            return httpx.Response(404)

        monkeypatch.setattr(client._client, "delete", mock_delete)
        with pytest.raises(NextcloudError) as exc_info:
            await client.delete_file("Project Alpha", "missing.bcf")
        assert exc_info.value.status_code == 404

    async def test_ensure_directory(self, client: NextcloudClient, monkeypatch):
        """ensure_directory() creates each path segment."""
        mkcol_calls: list[str] = []

        async def mock_request(method, url, **kwargs):
            mkcol_calls.append(url)
            return httpx.Response(201)

        monkeypatch.setattr(client._client, "request", mock_request)
        await client.ensure_directory(
            "Projects/Test/99_overige_documenten/bim-validator"
        )
        assert len(mkcol_calls) == 4

    async def test_ensure_directory_exists(
        self, client: NextcloudClient, monkeypatch
    ):
        """ensure_directory() handles 405 (already exists) gracefully."""
        async def mock_request(method, url, **kwargs):
            return httpx.Response(405)

        monkeypatch.setattr(client._client, "request", mock_request)
        # Should not raise
        await client.ensure_directory("Projects/Existing")

    async def test_test_connection_success(
        self, client: NextcloudClient, monkeypatch
    ):
        """test_connection() returns True on 207."""
        async def mock_propfind(path, depth="0"):
            return httpx.Response(207)

        monkeypatch.setattr(client, "_propfind", mock_propfind)
        result = await client.test_connection()
        assert result is True

    async def test_test_connection_failure(
        self, client: NextcloudClient, monkeypatch
    ):
        """test_connection() returns False on connection error."""
        async def mock_propfind(path, depth="0"):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(client, "_propfind", mock_propfind)
        result = await client.test_connection()
        assert result is False


class TestNextcloudError:
    """Test NextcloudError exception."""

    def test_error_with_status(self):
        """NextcloudError stores status code."""
        err = NextcloudError("Not found", status_code=404)
        assert str(err) == "Not found"
        assert err.status_code == 404

    def test_error_without_status(self):
        """NextcloudError works without status code."""
        err = NextcloudError("Connection failed")
        assert str(err) == "Connection failed"
        assert err.status_code is None
