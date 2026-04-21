"""
Project API router — persistent project and file management.

Endpoints for CRUD on projects, and upload/download/delete of
IFC, BCF, and IDS files within projects. Files are stored on disk
under PROJECT_FILES_DIR/{project_id}/{file_type}/.

Also provides .wefc envelope endpoints that bridge the persistent
project (DB row) to its corresponding tenant Nextcloud folder.
"""

import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.database import get_session
from server.models.db_models import Project, ProjectFile
from server.nextcloud_client import (
    MANIFEST_FILENAME,
    NextcloudError,
    get_nc_client,
)
from server.tenant_config import TenantConfig, get_tenants
from server.volume_reader import VolumeReader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["projects"])

# Default tenant slug when multi-tenant resolution is not yet active
DEFAULT_TENANT_SLUG = "3bm"

# Base directory for project file storage
PROJECT_FILES_DIR = Path(
    os.environ.get("PROJECT_FILES_DIR", "/data/projects")
)

# Maximum file sizes
MAX_IFC_SIZE = 1024 * 1024 * 1024  # 1 GB
MAX_BCF_SIZE = 100 * 1024 * 1024   # 100 MB
MAX_IDS_SIZE = 5 * 1024 * 1024     # 5 MB

ALLOWED_TYPES = {"ifc", "bcf", "ids"}
TYPE_EXTENSIONS = {
    "ifc": {".ifc", ".ifcx"},
    "bcf": {".bcf", ".bcfzip"},
    "ids": {".ids", ".xml"},
}
TYPE_SIZE_LIMITS = {
    "ifc": MAX_IFC_SIZE,
    "bcf": MAX_BCF_SIZE,
    "ids": MAX_IDS_SIZE,
}


def _project_dir(project_id: str, file_type: str | None = None) -> Path:
    """Get the disk directory for a project or a file type within it."""
    base = PROJECT_FILES_DIR / project_id
    if file_type:
        return base / file_type
    return base


def _resolve_tenant_slug(request: Request) -> str | None:
    """Resolve the caller's tenant slug from forward-auth headers.

    Soft variant of :func:`_resolve_tenant_from_request` — used by
    endpoints that need tenant scoping but must remain callable in
    dev/local runs where no Authentik is in front of the service.

    Returns:
        The tenant slug, or ``None`` when the request is not behind
        Authentik (no ``X-authentik-username`` header). ``None`` signals
        "no tenant context" and causes the caller to return the
        backward-compat unscoped view.
    """
    # If the request is not behind Authentik at all, skip tenant scoping.
    # This preserves the existing local-dev / auth-disabled behaviour.
    if not request.headers.get("X-authentik-username"):
        return None

    # Header is set by Authentik when the openaec_profile scope is
    # mapped. Fall back to the default slug when the user has no tenant
    # attribute yet (e.g. legacy accounts).
    return (
        request.headers.get("X-Authentik-Meta-Tenant")
        or request.query_params.get("tenant")
        or DEFAULT_TENANT_SLUG
    )


async def _get_project_for_tenant(
    project_id: str,
    session: AsyncSession,
    request: Request,
) -> Project:
    """Fetch a project by id, enforcing tenant isolation.

    Soft-fail: when the request carries no Authentik identity header
    (dev/local runs without forward-auth), this behaves like a plain
    ``session.get(Project, project_id)`` and raises ``404`` on missing
    rows. When a tenant is resolved, the query is narrowed with an
    ``== tenant_slug`` predicate and any mismatch (including the NULL
    legacy rows) returns ``404`` — deliberately not ``403``, so that
    the response does not disclose whether a project with that id
    exists in another tenant.
    """
    tenant_slug = _resolve_tenant_slug(request)

    if tenant_slug is None:
        project = await session.get(Project, project_id)
    else:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.tenant == tenant_slug,
        )
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(404, f"Project not found: {project_id}")
    return project


# ── Projects CRUD ─────────────────────────────────────────────


@router.get("/projects")
async def list_projects(request: Request):
    """List projects visible to the caller.

    When the request arrives behind Authentik forward-auth, the caller's
    tenant slug is resolved from ``X-Authentik-Meta-Tenant`` and the
    listing is filtered to projects stamped with that slug. Legacy rows
    with ``tenant IS NULL`` are excluded from tenant-scoped views to
    prevent data leaks across tenants — they must be migrated or
    re-stamped before they become visible again.

    When no Authentik header is present (dev/local or auth disabled),
    the full list is returned for backward compatibility.
    """
    tenant_slug = _resolve_tenant_slug(request)

    async with get_session() as session:
        stmt = select(Project).order_by(Project.updated_at.desc())
        if tenant_slug is not None:
            stmt = stmt.where(Project.tenant == tenant_slug)
        result = await session.execute(stmt)
        projects = result.scalars().all()
        return {"projects": [p.to_summary() for p in projects]}


@router.post("/projects", status_code=201)
async def create_project(
    request: Request,
    name: str = Form("Nieuw project"),
    description: str = Form(None),
):
    """Create a new project, stamped with the caller's tenant slug."""
    tenant_slug = _resolve_tenant_slug(request)

    async with get_session() as session:
        project = Project(
            name=name,
            description=description,
            tenant=tenant_slug,
        )
        session.add(project)
        await session.flush()

        # Create disk directories
        for ftype in ALLOWED_TYPES:
            _project_dir(project.id, ftype).mkdir(parents=True, exist_ok=True)

        logger.info(
            "Created project: %s (%s, tenant=%s)",
            project.id,
            name,
            tenant_slug,
        )
        return project.to_dict()


@router.get("/projects/{project_id}")
async def get_project(project_id: str, request: Request):
    """Get project details including file list."""
    async with get_session() as session:
        project = await _get_project_for_tenant(project_id, session, request)
        return project.to_dict()


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    request: Request,
    name: str = Form(None),
    description: str = Form(None),
):
    """Update project name and/or description."""
    async with get_session() as session:
        project = await _get_project_for_tenant(project_id, session, request)

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description

        logger.info("Updated project: %s", project_id)
        return project.to_dict()


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, request: Request):
    """Delete a project and all its files."""
    async with get_session() as session:
        project = await _get_project_for_tenant(project_id, session, request)

        # Remove files from disk
        project_dir = _project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)

        await session.delete(project)
        logger.info("Deleted project: %s", project_id)
        return {"success": True, "message": f"Project {project_id} deleted"}


# ── File Management ───────────────────────────────────────────


@router.get("/projects/{project_id}/files")
async def list_files(
    project_id: str,
    request: Request,
    file_type: str | None = None,
):
    """List files in a project, optionally filtered by type."""
    async with get_session() as session:
        project = await _get_project_for_tenant(project_id, session, request)

        files = project.files
        if file_type:
            files = [f for f in files if f.file_type == file_type]

        return {
            "projectId": project_id,
            "files": [f.to_dict() for f in files],
        }


@router.post("/projects/{project_id}/files", status_code=201)
async def upload_file(
    project_id: str,
    request: Request,
    file: UploadFile = File(..., description="IFC, BCF, or IDS file"),
    file_type: str = Form(..., description="File type: ifc, bcf, or ids"),
):
    """Upload a file to a project."""
    # Validate file type
    if file_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Invalid file_type: {file_type}. Use: {ALLOWED_TYPES}")

    if not file.filename:
        raise HTTPException(400, "Filename is required")

    # Validate extension
    ext = Path(file.filename).suffix.lower()
    allowed_exts = TYPE_EXTENSIONS.get(file_type, set())
    if ext not in allowed_exts:
        raise HTTPException(
            400,
            f"Invalid extension '{ext}' for type '{file_type}'. Allowed: {allowed_exts}",
        )

    # Check project exists and belongs to the caller's tenant
    async with get_session() as session:
        await _get_project_for_tenant(project_id, session, request)

        # Read file content with size limit
        size_limit = TYPE_SIZE_LIMITS[file_type]
        content = await file.read()
        if not content:
            raise HTTPException(400, "File is empty")
        if len(content) > size_limit:
            raise HTTPException(
                413,
                f"File too large: {len(content)} bytes (max {size_limit})",
            )

        # Save to disk
        target_dir = _project_dir(project_id, file_type)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename.replace(' ', '_')}"
        disk_path = target_dir / safe_name

        with open(disk_path, "wb") as f:
            f.write(content)

        # Create DB record
        relative_path = f"{project_id}/{file_type}/{safe_name}"
        project_file = ProjectFile(
            project_id=project_id,
            file_type=file_type,
            file_name=file.filename,
            file_size=len(content),
            disk_path=relative_path,
        )
        session.add(project_file)
        await session.flush()

        logger.info(
            "Uploaded %s to project %s: %s (%d bytes)",
            file_type,
            project_id,
            file.filename,
            len(content),
        )
        return project_file.to_dict()


@router.get("/projects/{project_id}/files/{file_id}")
async def download_file(project_id: str, file_id: str, request: Request):
    """Download a file from a project."""
    async with get_session() as session:
        # Enforce tenant isolation on the parent project first — a
        # stale/guessed file_id must not be resolvable across tenants.
        await _get_project_for_tenant(project_id, session, request)

        project_file = await session.get(ProjectFile, file_id)
        if not project_file or project_file.project_id != project_id:
            raise HTTPException(404, "File not found")

        file_path = PROJECT_FILES_DIR / project_file.disk_path
        if not file_path.exists():
            raise HTTPException(404, "File not found on disk")

        return FileResponse(
            path=file_path,
            filename=project_file.file_name,
            media_type="application/octet-stream",
        )


@router.delete("/projects/{project_id}/files/{file_id}")
async def delete_file(project_id: str, file_id: str, request: Request):
    """Delete a file from a project."""
    async with get_session() as session:
        # Enforce tenant isolation on the parent project first.
        await _get_project_for_tenant(project_id, session, request)

        project_file = await session.get(ProjectFile, file_id)
        if not project_file or project_file.project_id != project_id:
            raise HTTPException(404, "File not found")

        # Remove from disk
        file_path = PROJECT_FILES_DIR / project_file.disk_path
        file_path.unlink(missing_ok=True)

        await session.delete(project_file)
        logger.info(
            "Deleted file %s from project %s", file_id, project_id
        )
        return {"success": True, "message": f"File {file_id} deleted"}


# ── .wefc envelope (bridges persistent project to tenant cloud) ──


def _resolve_tenant_from_request(request: Request) -> TenantConfig:
    """Resolve tenant from Authentik forward-auth headers.

    Looks for X-Authentik-Meta-Tenant first (custom OpenAEC profile
    scope), falls back to a query parameter ``tenant`` and finally to
    the default tenant slug.

    Raises:
        HTTPException 401 when no Authentik user header is present.
        HTTPException 503 when no tenants are configured at all.
        HTTPException 403 when the requested tenant slug is unknown.
    """
    # Auth gate — Authentik forward-auth always sets a username header
    # for authenticated requests. Reject when missing.
    if not request.headers.get("X-authentik-username"):
        raise HTTPException(401, "Not authenticated")

    registry = get_tenants()
    if not registry.is_configured:
        raise HTTPException(503, "Cloud storage not configured (no tenants)")

    # Header is set by Authentik when the openaec_profile scope is mapped.
    slug = (
        request.headers.get("X-Authentik-Meta-Tenant")
        or request.query_params.get("tenant")
        or DEFAULT_TENANT_SLUG
    )

    config = registry.get(slug)
    if not config:
        raise HTTPException(403, f"Unknown tenant: {slug}")
    return config


def _nc_error_to_http(exc: Exception) -> HTTPException:
    """Map a NextcloudError to an HTTP response."""
    if isinstance(exc, NextcloudError) and exc.status_code:
        return HTTPException(status_code=exc.status_code, detail=str(exc))
    return HTTPException(status_code=502, detail=f"Cloud backend error: {exc}")


def _wefc_filename_for_project(project: Project) -> str:
    """Return the .wefc filename used for a persistent project.

    Uses a stable, project-id derived name so multiple projects with
    the same display name do not collide in the same Nextcloud folder.
    The plain project.wefc remains reserved for the legacy/default
    container.
    """
    return f"project-{project.id}.wefc"


def _project_folder_name(project: Project) -> str:
    """Return the Nextcloud folder name for a persistent project.

    Convention: all v2 project envelopes live under a single shared
    ``Projects/`` namespace, in a per-project folder derived from the
    project name. Falls back to the project id if no name is set.
    """
    name = (project.name or "").strip()
    if not name:
        return f"project-{project.id}"
    return name


@router.get("/projects/{project_id}/wefc")
async def get_project_wefc(project_id: str, request: Request):
    """Return the .wefc envelope for a persistent project.

    Resolves the tenant from forward-auth headers, locates the
    project's Nextcloud folder, and reads the manifest via the volume
    mount when available, falling back to WebDAV otherwise.
    """
    config = _resolve_tenant_from_request(request)

    async with get_session() as session:
        project = await _get_project_for_tenant(project_id, session, request)
        folder = _project_folder_name(project)
        manifest_name = _wefc_filename_for_project(project)

    # Fast path: read from the tenant's volume mount
    reader = VolumeReader(config)
    if reader.available:
        manifest = reader.read_manifest(folder, manifest_name)
        if manifest is None:
            # Backward-compat: also try the default project.wefc for projects
            # that were saved before the project-id naming convention.
            manifest = reader.read_manifest(folder, MANIFEST_FILENAME)
        if manifest is not None:
            return JSONResponse(content=manifest)

    # Fallback: WebDAV
    client = get_nc_client(config)
    try:
        manifest = await client.read_manifest(folder, manifest_name)
        if manifest is None:
            manifest = await client.read_manifest(folder, MANIFEST_FILENAME)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    if manifest is None:
        raise HTTPException(
            404,
            f"No .wefc envelope for project {project_id} (folder: {folder})",
        )
    return JSONResponse(content=manifest)


@router.put("/projects/{project_id}/wefc")
async def put_project_wefc(
    project_id: str,
    request: Request,
    manifest: dict[str, Any],
):
    """Write the .wefc envelope for a persistent project.

    Validates that the body is a dict, ensures the manifest header is
    present and current, and writes via WebDAV (always — volume mount
    is read-only for the bim-validator process).
    """
    config = _resolve_tenant_from_request(request)

    if not isinstance(manifest, dict):
        raise HTTPException(400, "Body must be a JSON object")

    async with get_session() as session:
        project = await _get_project_for_tenant(project_id, session, request)
        folder = _project_folder_name(project)
        manifest_name = _wefc_filename_for_project(project)

    # Ensure the manifest header is up to date
    header = manifest.get("header") if isinstance(manifest.get("header"), dict) else {}
    header.setdefault("schema", "WeFC")
    header.setdefault("schema_version", "1.1.0")
    header.setdefault("fileId", str(uuid.uuid4()))
    header["timestamp"] = datetime.now(timezone.utc).isoformat()
    header["application"] = "bim-validator"
    header["projectId"] = project_id
    header["projectName"] = project.name
    manifest["header"] = header

    # Touch the project's updated_at so the listing reflects the save.
    async with get_session() as session:
        # Tenant already verified above; use a direct session.get here
        # because a missing row at this point should be an exceptional
        # transient state (deleted between the check and this block),
        # and we don't want to raise a spurious 404 after a successful
        # WebDAV write.
        db_project = await session.get(Project, project_id)
        if db_project is not None:
            db_project.updated_at = datetime.now(timezone.utc)

    client = get_nc_client(config)
    try:
        await client.write_manifest(folder, manifest, manifest_name)
    except Exception as exc:
        raise _nc_error_to_http(exc) from exc

    logger.info(
        "Wrote .wefc envelope for project %s (folder=%s, file=%s, tenant=%s)",
        project_id,
        folder,
        manifest_name,
        config.slug,
    )

    return JSONResponse(
        content={
            "success": True,
            "projectId": project_id,
            "folder": folder,
            "manifest": manifest_name,
            "tenant": config.slug,
        }
    )
