"""
Cloud storage API router — hybrid Nextcloud I/O.

Reads via direct volume mount (fast), writes via WebDAV (NC stays in sync).
Multi-tenant: tenant resolved from X-Tenant header or query parameter.
Falls back to WebDAV for reads when volume mount is unavailable.
"""

import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from server.models.cloud import (
    CloudDeleteResponse,
    CloudFileItem,
    CloudFilesResponse,
    CloudProjectItem,
    CloudProjectsResponse,
    CloudStatusResponse,
    CloudUploadResponse,
)
from server.nextcloud_client import NextcloudError, get_nc_client
from server.tenant_config import TenantConfig, get_tenant, get_tenants
from server.volume_reader import VolumeReader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cloud", tags=["cloud"])

# Default tenant slug when multi-tenant is not yet active
DEFAULT_TENANT = "3bm"


def _resolve_tenant(tenant: str | None = None) -> TenantConfig:
    """Resolve tenant from parameter, falling back to default."""
    registry = get_tenants()
    if not registry.is_configured:
        raise HTTPException(503, "Cloud storage is not configured (no tenants)")

    slug = tenant or DEFAULT_TENANT
    config = registry.get(slug)
    if not config:
        raise HTTPException(404, f"Unknown tenant: {slug}")
    return config


def _get_reader(config: TenantConfig) -> VolumeReader:
    """Get a VolumeReader for the given tenant."""
    return VolumeReader(config)


def _nc_error_to_http(exc: Exception) -> HTTPException:
    """Convert a NextcloudError to an HTTPException."""
    if isinstance(exc, NextcloudError) and exc.status_code:
        return HTTPException(status_code=exc.status_code, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


# ── Status ─────────────────────────────────────────────────────


@router.get("/status")
async def cloud_status(tenant: str | None = Query(None)):
    """Check if cloud storage is enabled and reachable."""
    registry = get_tenants()
    if not registry.is_configured:
        return CloudStatusResponse(enabled=False, connected=False)

    config = _resolve_tenant(tenant)
    reader = _get_reader(config)

    # Volume mount = fast path
    if reader.available:
        return CloudStatusResponse(enabled=True, connected=True)

    # Fallback: test WebDAV connection
    client = get_nc_client(config)
    try:
        connected = await client.test_connection()
    except Exception:
        connected = False

    return CloudStatusResponse(enabled=True, connected=connected)


# ── Projects ───────────────────────────────────────────────────


@router.get("/projects")
async def cloud_list_projects(tenant: str | None = Query(None)):
    """List available project folders."""
    config = _resolve_tenant(tenant)
    reader = _get_reader(config)

    # Fast path: read from volume mount
    if reader.available:
        projects = reader.list_projects()
        return CloudProjectsResponse(
            projects=[
                CloudProjectItem(name=p.name, last_modified="")
                for p in projects
            ]
        )

    # Fallback: WebDAV
    client = get_nc_client(config)
    try:
        items = await client.list_projects()
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    return CloudProjectsResponse(
        projects=[
            CloudProjectItem(name=item.name, last_modified=item.last_modified)
            for item in items
        ]
    )


# ── File listing ───────────────────────────────────────────────


@router.get("/projects/{project}/files")
async def cloud_list_files(
    project: str,
    category: str = Query("output", regex="^(bim|output)$"),
    tenant: str | None = Query(None),
):
    """List files in a project directory.

    Args:
        project: Project folder name.
        category: 'bim' for 70_BIM (IFC/IDS), 'output' for tool output files.
        tenant: Tenant slug (optional, defaults to 3bm).
    """
    config = _resolve_tenant(tenant)
    reader = _get_reader(config)

    # Fast path: volume mount
    if reader.available:
        if category == "bim":
            files = reader.list_bim_files(project)
        else:
            files = reader.list_output_files(project)

        return CloudFilesResponse(
            project=project,
            files=[
                CloudFileItem(
                    name=f.name,
                    size=f.size,
                    last_modified=f.last_modified,
                )
                for f in files
            ],
        )

    # Fallback: WebDAV (only lists tool output files)
    client = get_nc_client(config)
    try:
        items = await client.list_files(project)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    return CloudFilesResponse(
        project=project,
        files=[
            CloudFileItem(
                name=item.name,
                size=item.content_length,
                last_modified=item.last_modified,
            )
            for item in items
        ],
    )


# ── File download (read) ──────────────────────────────────────


@router.get("/projects/{project}/files/{filename}")
async def cloud_download_file(
    project: str,
    filename: str,
    category: str = Query("output", regex="^(bim|output)$"),
    tenant: str | None = Query(None),
):
    """Download a file from a project.

    Uses direct volume mount for fast I/O, falls back to WebDAV.
    """
    config = _resolve_tenant(tenant)
    reader = _get_reader(config)

    # Fast path: stream from volume mount
    if reader.available:
        from server.volume_reader import BIM_SUBDIR, OUTPUT_SUBDIR

        subdir = BIM_SUBDIR if category == "bim" else OUTPUT_SUBDIR
        file_path = reader.get_file_path(project, filename, subdir)
        if file_path:
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/octet-stream",
            )
        raise HTTPException(404, f"File not found: {filename}")

    # Fallback: WebDAV download
    client = get_nc_client(config)
    try:
        content = await client.download_file(project, filename)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── File upload (write — always via WebDAV) ────────────────────


@router.put("/projects/{project}/files/{filename}")
async def cloud_upload_file(
    project: str,
    filename: str,
    file: UploadFile = File(...),
    tenant: str | None = Query(None),
):
    """Upload a file to a project's tool subdirectory via WebDAV."""
    config = _resolve_tenant(tenant)
    client = get_nc_client(config)

    content = await file.read()
    try:
        await client.upload_file(project, filename, content)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    return CloudUploadResponse(success=True, project=project, filename=filename)


# ── File delete (write — always via WebDAV) ────────────────────


@router.delete("/projects/{project}/files/{filename}")
async def cloud_delete_file(
    project: str,
    filename: str,
    tenant: str | None = Query(None),
):
    """Delete a file from a project's tool subdirectory via WebDAV."""
    config = _resolve_tenant(tenant)
    client = get_nc_client(config)

    try:
        await client.delete_file(project, filename)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    return CloudDeleteResponse(success=True, project=project, filename=filename)


# ── Convenience: save BCF ──────────────────────────────────────


@router.post("/projects/{project}/save")
async def cloud_save_bcf(
    project: str,
    file: UploadFile = File(...),
    filename: str = Form("validation.bcf"),
    tenant: str | None = Query(None),
):
    """Save a BCF file to a project's cloud folder via WebDAV."""
    config = _resolve_tenant(tenant)
    client = get_nc_client(config)

    content = await file.read()
    try:
        await client.upload_file(project, filename, content)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    return CloudUploadResponse(success=True, project=project, filename=filename)
