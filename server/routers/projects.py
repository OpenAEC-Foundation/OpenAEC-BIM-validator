"""
Project API router — persistent project and file management.

Endpoints for CRUD on projects, and upload/download/delete of
IFC, BCF, and IDS files within projects. Files are stored on disk
under PROJECT_FILES_DIR/{project_id}/{file_type}/.
"""

import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from server.database import get_session
from server.models.db_models import Project, ProjectFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["projects"])

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


# ── Projects CRUD ─────────────────────────────────────────────


@router.get("/projects")
async def list_projects():
    """List all projects."""
    async with get_session() as session:
        result = await session.execute(
            select(Project).order_by(Project.updated_at.desc())
        )
        projects = result.scalars().all()
        return {"projects": [p.to_summary() for p in projects]}


@router.post("/projects", status_code=201)
async def create_project(
    name: str = Form("Nieuw project"),
    description: str = Form(None),
):
    """Create a new project."""
    async with get_session() as session:
        project = Project(name=name, description=description)
        session.add(project)
        await session.flush()

        # Create disk directories
        for ftype in ALLOWED_TYPES:
            _project_dir(project.id, ftype).mkdir(parents=True, exist_ok=True)

        logger.info("Created project: %s (%s)", project.id, name)
        return project.to_dict()


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details including file list."""
    async with get_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, f"Project not found: {project_id}")
        return project.to_dict()


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    name: str = Form(None),
    description: str = Form(None),
):
    """Update project name and/or description."""
    async with get_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, f"Project not found: {project_id}")

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description

        logger.info("Updated project: %s", project_id)
        return project.to_dict()


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all its files."""
    async with get_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, f"Project not found: {project_id}")

        # Remove files from disk
        project_dir = _project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)

        await session.delete(project)
        logger.info("Deleted project: %s", project_id)
        return {"success": True, "message": f"Project {project_id} deleted"}


# ── File Management ───────────────────────────────────────────


@router.get("/projects/{project_id}/files")
async def list_files(project_id: str, file_type: str | None = None):
    """List files in a project, optionally filtered by type."""
    async with get_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, f"Project not found: {project_id}")

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

    # Check project exists
    async with get_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, f"Project not found: {project_id}")

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
async def download_file(project_id: str, file_id: str):
    """Download a file from a project."""
    async with get_session() as session:
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
async def delete_file(project_id: str, file_id: str):
    """Delete a file from a project."""
    async with get_session() as session:
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
