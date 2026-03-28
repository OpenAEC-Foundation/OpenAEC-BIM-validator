"""
Nextcloud WebDAV client for cloud storage integration.

Provides async file operations (list, upload, download, delete) against
a Nextcloud instance using WebDAV. Authentication uses Basic auth with
a service account. Multi-tenant: one client instance per tenant.

Usage:
    client = NextcloudClient(
        base_url="https://cloud.example.com",
        username="service-user",
        password="secret",
    )
    projects = await client.list_projects()

    # Or from tenant config:
    client = NextcloudClient.from_tenant(tenant_config)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import quote, unquote

import httpx

from server.tenant_config import TenantConfig

DAV_NS = {"d": "DAV:"}
TOOL_SLUG = "bim-validator"
PROJECTS_ROOT = "Projects"


class NextcloudError(Exception):
    """Raised when a Nextcloud WebDAV request fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class DavItem:
    """Represents a single WebDAV resource."""

    name: str
    href: str
    is_collection: bool
    content_length: int
    last_modified: str


class NextcloudClient:
    """Async Nextcloud WebDAV client.

    Args:
        base_url: Nextcloud instance URL (e.g. https://cloud.example.com).
        username: Service account username.
        password: Service account password.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._webdav_root = f"{self._base_url}/remote.php/dav/files/{quote(username, safe='')}"
        self._client = httpx.AsyncClient(
            auth=httpx.BasicAuth(username, password),
            timeout=timeout,
        )

    @classmethod
    def from_tenant(cls, tenant: TenantConfig) -> NextcloudClient:
        """Create a client from a TenantConfig."""
        return cls(
            base_url=tenant.nextcloud_url,
            username=tenant.service_user,
            password=tenant.service_pass,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ── Public API ──────────────────────────────────────────────

    async def test_connection(self) -> bool:
        """Check if the Nextcloud instance is reachable and credentials work."""
        try:
            resp = await self._propfind(f"{PROJECTS_ROOT}/", depth="0")
            return resp.status_code in (207, 404)
        except (httpx.HTTPError, NextcloudError):
            return False

    async def list_projects(self) -> list[DavItem]:
        """List project folders under Projects/.

        Returns:
            List of DavItem representing project directories.
        """
        items = await self._list_directory(f"{PROJECTS_ROOT}/")
        return [item for item in items if item.is_collection]

    async def list_files(self, project_name: str) -> list[DavItem]:
        """List BCF files in a project's tool subdirectory.

        Args:
            project_name: Name of the project folder.

        Returns:
            List of DavItem representing files.
        """
        path = self._tool_path(project_name)
        try:
            items = await self._list_directory(path)
            return [item for item in items if not item.is_collection]
        except NextcloudError as exc:
            if exc.status_code == 404:
                return []
            raise

    async def download_file(self, project_name: str, filename: str) -> bytes:
        """Download a file from the project tool directory.

        Args:
            project_name: Name of the project folder.
            filename: Name of the file to download.

        Returns:
            Raw file bytes.
        """
        path = f"{self._tool_path(project_name)}/{quote(filename, safe='')}"
        url = f"{self._webdav_root}/{path}"

        try:
            resp = await self._client.get(url)
        except httpx.HTTPError as exc:
            raise NextcloudError(f"Connection error: {exc}") from exc

        if resp.status_code == 404:
            raise NextcloudError(f"File not found: {filename}", status_code=404)
        if resp.status_code >= 400:
            raise NextcloudError(
                f"Download failed: {resp.status_code}", status_code=resp.status_code
            )

        return resp.content

    async def upload_file(
        self, project_name: str, filename: str, content: bytes
    ) -> None:
        """Upload a file to the project tool directory.

        Creates intermediate directories if they don't exist.

        Args:
            project_name: Name of the project folder.
            filename: Target filename.
            content: File content as bytes.
        """
        tool_path = self._tool_path(project_name)
        await self.ensure_directory(tool_path)

        url = f"{self._webdav_root}/{tool_path}/{quote(filename, safe='')}"

        try:
            resp = await self._client.put(url, content=content)
        except httpx.HTTPError as exc:
            raise NextcloudError(f"Connection error: {exc}") from exc

        if resp.status_code >= 400:
            raise NextcloudError(
                f"Upload failed: {resp.status_code}", status_code=resp.status_code
            )

    async def delete_file(self, project_name: str, filename: str) -> None:
        """Delete a file from the project tool directory.

        Args:
            project_name: Name of the project folder.
            filename: Name of the file to delete.
        """
        path = f"{self._tool_path(project_name)}/{quote(filename, safe='')}"
        url = f"{self._webdav_root}/{path}"

        try:
            resp = await self._client.delete(url)
        except httpx.HTTPError as exc:
            raise NextcloudError(f"Connection error: {exc}") from exc

        if resp.status_code == 404:
            raise NextcloudError(f"File not found: {filename}", status_code=404)
        if resp.status_code >= 400:
            raise NextcloudError(
                f"Delete failed: {resp.status_code}", status_code=resp.status_code
            )

    async def ensure_directory(self, path: str) -> None:
        """Recursively create directories via MKCOL.

        Args:
            path: Relative path within the WebDAV root to ensure exists.
        """
        parts = path.strip("/").split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            url = f"{self._webdav_root}/{current}"
            try:
                resp = await self._client.request("MKCOL", url)
            except httpx.HTTPError as exc:
                raise NextcloudError(f"Connection error: {exc}") from exc

            # 201 = created, 405 = already exists — both OK
            if resp.status_code not in (201, 405):
                if resp.status_code >= 400:
                    raise NextcloudError(
                        f"MKCOL failed for {current}: {resp.status_code}",
                        status_code=resp.status_code,
                    )

    # ── Private helpers ─────────────────────────────────────────

    def _tool_path(self, project_name: str) -> str:
        """Build the relative path to a project's tool subdirectory."""
        safe_project = quote(project_name, safe="")
        return f"{PROJECTS_ROOT}/{safe_project}/99_overige_documenten/{TOOL_SLUG}"

    async def _propfind(
        self, path: str, depth: str = "1"
    ) -> httpx.Response:
        """Execute a PROPFIND request.

        Args:
            path: Relative path within the WebDAV root.
            depth: WebDAV Depth header value ("0" or "1").

        Returns:
            The raw httpx.Response.
        """
        url = f"{self._webdav_root}/{path.lstrip('/')}"
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<d:propfind xmlns:d="DAV:">'
            "<d:prop>"
            "<d:resourcetype/>"
            "<d:getcontentlength/>"
            "<d:getlastmodified/>"
            "<d:displayname/>"
            "</d:prop>"
            "</d:propfind>"
        )

        try:
            resp = await self._client.request(
                "PROPFIND",
                url,
                content=body.encode(),
                headers={
                    "Content-Type": "application/xml",
                    "Depth": depth,
                },
            )
        except httpx.HTTPError as exc:
            raise NextcloudError(f"Connection error: {exc}") from exc

        if resp.status_code == 404:
            raise NextcloudError(f"Path not found: {path}", status_code=404)
        if resp.status_code >= 400:
            raise NextcloudError(
                f"PROPFIND failed: {resp.status_code}",
                status_code=resp.status_code,
            )

        return resp

    async def _list_directory(self, path: str) -> list[DavItem]:
        """List contents of a WebDAV directory.

        Args:
            path: Relative path within the WebDAV root.

        Returns:
            List of DavItem, excluding the directory itself.
        """
        resp = await self._propfind(path, depth="1")
        return self._parse_multistatus(resp.content, path)

    def _parse_multistatus(self, xml_bytes: bytes, base_path: str) -> list[DavItem]:
        """Parse a WebDAV multistatus XML response.

        Args:
            xml_bytes: Raw XML response body.
            base_path: The requested path, used to filter out the parent entry.

        Returns:
            List of parsed DavItem objects.
        """
        root = ET.fromstring(xml_bytes)
        items: list[DavItem] = []

        for response in root.findall("d:response", DAV_NS):
            href_el = response.find("d:href", DAV_NS)
            if href_el is None or href_el.text is None:
                continue

            href = unquote(href_el.text).rstrip("/")
            propstat = response.find("d:propstat", DAV_NS)
            if propstat is None:
                continue

            prop = propstat.find("d:prop", DAV_NS)
            if prop is None:
                continue

            # Detect collection
            restype = prop.find("d:resourcetype", DAV_NS)
            is_collection = (
                restype is not None
                and restype.find("d:collection", DAV_NS) is not None
            )

            # Extract name from href (last path segment)
            name_parts = href.rsplit("/", 1)
            name = name_parts[-1] if len(name_parts) > 1 else href

            # Display name override
            display_el = prop.find("d:displayname", DAV_NS)
            if display_el is not None and display_el.text:
                name = display_el.text

            # Content length
            length_el = prop.find("d:getcontentlength", DAV_NS)
            content_length = int(length_el.text) if length_el is not None and length_el.text else 0

            # Last modified
            modified_el = prop.find("d:getlastmodified", DAV_NS)
            last_modified = modified_el.text if modified_el is not None and modified_el.text else ""

            # Skip the directory itself (base path)
            # Compare decoded versions to handle URL-encoded paths
            decoded_base = unquote(base_path).rstrip("/")
            if href.rstrip("/").endswith(decoded_base):
                continue

            items.append(
                DavItem(
                    name=name,
                    href=href_el.text,
                    is_collection=is_collection,
                    content_length=content_length,
                    last_modified=last_modified,
                )
            )

        return items


# ── Multi-tenant client registry ───────────────────────────────

_clients: dict[str, NextcloudClient] = {}


def get_nc_client(tenant: TenantConfig) -> NextcloudClient:
    """Get or create a NextcloudClient for the given tenant."""
    if tenant.slug not in _clients:
        _clients[tenant.slug] = NextcloudClient.from_tenant(tenant)
    return _clients[tenant.slug]


async def close_all_clients() -> None:
    """Close all cached clients. Call on app shutdown."""
    for client in _clients.values():
        await client.close()
    _clients.clear()
