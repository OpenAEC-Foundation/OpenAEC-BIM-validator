"""
Cloud storage API router — hybrid Nextcloud I/O.

Reads via direct volume mount (fast), writes via WebDAV (NC stays in sync).
Multi-tenant: tenant resolved from X-Tenant header or query parameter.
Falls back to WebDAV for reads when volume mount is unavailable.

Supports the new project container model:
- models/ for IFC/BIM files (read)
- validation/ for validator output (write)
- project.wefc manifest for linking objects
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse, Response

from server.models.cloud import (
    CloudDeleteResponse,
    CloudFileItem,
    CloudFilesResponse,
    CloudProjectItem,
    CloudProjectsResponse,
    CloudStatusResponse,
    CloudUploadResponse,
)
from server.nextcloud_client import (
    DIR_MODELS,
    DIR_VALIDATION,
    NextcloudError,
    get_nc_client,
)
from server.tenant_config import TenantConfig, get_tenant, get_tenants
from server.volume_reader import (
    LEGACY_BIM_SUBDIR,
    LEGACY_OUTPUT_SUBDIR,
    VolumeReader,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cloud", tags=["cloud"])

# Default tenant slug when multi-tenant is not yet active
DEFAULT_TENANT = "3bm"


def _resolve_tenant(tenant: str | None = None) -> TenantConfig:
    """Resolve tenant from parameter, falling back to default."""
    registry = get_tenants()
    if not registry.is_configured:
        raise HTTPException(
            503, "Cloud storage is not configured (no tenants)"
        )

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
        return HTTPException(
            status_code=exc.status_code, detail=str(exc)
        )
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
    category: str = Query(
        "output", pattern="^(bim|output)$"
    ),
    tenant: str | None = Query(None),
):
    """List files in a project directory.

    Uses the new project container model paths with fallback to legacy:
    - category=bim: reads from models/ (fallback: 70_BIM/)
    - category=output: reads from validation/ (fallback: 99_overige_documenten/bim-validator/)

    Args:
        project: Project folder name.
        category: 'bim' for model files, 'output' for validation output.
        tenant: Tenant slug (optional, defaults to 3bm).
    """
    config = _resolve_tenant(tenant)
    reader = _get_reader(config)

    # Fast path: volume mount (includes fallback logic internally)
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

    # Fallback: WebDAV (includes fallback logic internally)
    client = get_nc_client(config)
    try:
        if category == "bim":
            items = await client.list_models(project)
        else:
            items = await client.list_validation_files(project)
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
    category: str = Query(
        "output", pattern="^(bim|output)$"
    ),
    tenant: str | None = Query(None),
):
    """Download a file from a project.

    Uses direct volume mount for fast I/O, falls back to WebDAV.
    Volume reader and WebDAV client both include fallback to legacy paths.
    """
    config = _resolve_tenant(tenant)
    reader = _get_reader(config)

    # Fast path: stream from volume mount (get_file_path has fallback)
    if reader.available:
        subdir = DIR_MODELS if category == "bim" else DIR_VALIDATION
        file_path = reader.get_file_path(
            project, filename, subdir
        )
        if file_path:
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/octet-stream",
            )
        raise HTTPException(404, f"File not found: {filename}")

    # Fallback: WebDAV download (has fallback to legacy paths)
    client = get_nc_client(config)
    try:
        if category == "bim":
            # Try models/ then 70_BIM/
            try:
                content = await client.download_from(
                    project, filename, DIR_MODELS
                )
            except NextcloudError as exc:
                if exc.status_code != 404:
                    raise
                content = await client.download_from(
                    project, filename, LEGACY_BIM_SUBDIR
                )
        else:
            content = await client.download_file(
                project, filename
            )
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
        },
    )


# ── File upload (write — always via WebDAV) ────────────────────


@router.put("/projects/{project}/files/{filename}")
async def cloud_upload_file(
    project: str,
    filename: str,
    file: UploadFile = File(...),
    category: str = Query("output", pattern="^(bim|output)$"),
    tenant: str | None = Query(None),
):
    """Upload a file to a project subdirectory via WebDAV.

    Args:
        project: Project folder name.
        filename: Target filename.
        category: 'bim' writes to models/, 'output' writes to validation/.
        tenant: Tenant slug (optional).
    """
    config = _resolve_tenant(tenant)
    client = get_nc_client(config)

    subdir = DIR_MODELS if category == "bim" else DIR_VALIDATION
    content = await file.read()
    try:
        await client.upload_to(project, filename, content, subdir)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    return CloudUploadResponse(
        success=True, project=project, filename=filename
    )


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


# ── Convenience: save validation result ───────────────────────


@router.post("/projects/{project}/save")
async def cloud_save_validation(
    project: str,
    file: UploadFile = File(...),
    filename: str = Form("validation.json"),
    model_guid: str | None = Form(None),
    tenant: str | None = Query(None),
):
    """Save a validation result to a project's validation/ folder.

    Writes the file via WebDAV and updates the project.wefc manifest
    with a WefcValidation object. If the manifest does not exist yet,
    it is created automatically.

    Args:
        project: Project folder name.
        file: Validation result file.
        filename: Target filename in validation/ directory.
        model_guid: Optional GUID of the IFC model that was validated.
        tenant: Tenant slug (optional).
    """
    config = _resolve_tenant(tenant)
    client = get_nc_client(config)

    content = await file.read()
    try:
        await client.upload_to_validation(
            project, filename, content
        )
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    # Update manifest with WefcValidation object
    now = datetime.now(timezone.utc).isoformat()
    validation_obj: dict[str, Any] = {
        "type": "WefcValidation",
        "guid": str(uuid.uuid4()),
        "name": f"BIM Validatie - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "path": f"{DIR_VALIDATION}/{filename}",
        "status": "active",
        "created": now,
        "modified": now,
    }
    if model_guid:
        validation_obj["model"] = f"wfc://{model_guid}"

    try:
        await client.upsert_manifest_object(
            project, validation_obj
        )
    except Exception as exc:
        # Manifest update is best-effort; log but don't fail
        logger.warning(
            "Failed to update manifest for %s: %s",
            project,
            exc,
        )

    return CloudUploadResponse(
        success=True, project=project, filename=filename
    )


# ── Manifest ──────────────────────────────────────────────────


@router.get("/projects/{project}/manifest")
async def cloud_get_manifest(
    project: str,
    tenant: str | None = Query(None),
):
    """Read the project.wefc manifest as JSON.

    Returns the full manifest if it exists. Uses volume mount for
    fast reads, falls back to WebDAV.
    """
    config = _resolve_tenant(tenant)
    reader = _get_reader(config)

    # Fast path: read from volume mount
    if reader.available:
        manifest = reader.read_manifest(project)
        if manifest is not None:
            return JSONResponse(content=manifest)

    # Fallback: WebDAV
    client = get_nc_client(config)
    try:
        manifest = await client.read_manifest(project)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    if manifest is None:
        raise HTTPException(
            404, f"No manifest found for project: {project}"
        )

    return JSONResponse(content=manifest)
