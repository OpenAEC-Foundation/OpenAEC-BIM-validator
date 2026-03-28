"""
Direct filesystem reader for Nextcloud volume mounts.

Reads project listings and file contents directly from the read-only
Nextcloud data volume, bypassing WebDAV for fast I/O on large files.

Falls back to None/empty when volume mount is not available,
so callers can use WebDAV as fallback.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from server.tenant_config import TenantConfig

logger = logging.getLogger(__name__)

TOOL_SLUG = "bim-validator"

# Subdirectories within a project
BIM_SUBDIR = "70_BIM"
OUTPUT_SUBDIR = f"99_overige_documenten/{TOOL_SLUG}"

# File extensions per category
BIM_EXTENSIONS = {".ifc", ".ifcx", ".ids", ".xml", ".bcf", ".bcfzip"}


@dataclass
class VolumeFileInfo:
    """Metadata for a file read from the volume mount."""

    name: str
    path: Path
    size: int
    last_modified: str  # ISO 8601


@dataclass
class VolumeProject:
    """A project directory found on the volume mount."""

    name: str
    path: Path


class VolumeReader:
    """Reads projects and files from a Nextcloud volume mount.

    Args:
        tenant: Tenant configuration with volume mount path.
    """

    def __init__(self, tenant: TenantConfig) -> None:
        self._tenant = tenant
        self._root = tenant.projects_root

    @property
    def available(self) -> bool:
        """Check if the volume mount is accessible."""
        return self._tenant.has_volume_mount

    def list_projects(self) -> list[VolumeProject]:
        """List all project directories in the group folder.

        Returns:
            List of VolumeProject, sorted by name.
        """
        if not self.available:
            return []

        projects = []
        try:
            for entry in self._root.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    projects.append(VolumeProject(name=entry.name, path=entry))
        except OSError as exc:
            logger.error("Failed to list projects: %s", exc)
            return []

        projects.sort(key=lambda p: p.name)
        return projects

    def list_bim_files(self, project_name: str) -> list[VolumeFileInfo]:
        """List BIM files (IFC/IDS/BCF) in a project's 70_BIM directory.

        Args:
            project_name: Name of the project directory.

        Returns:
            List of VolumeFileInfo for matching files.
        """
        bim_dir = self._root / project_name / BIM_SUBDIR
        return self._list_files_in(bim_dir, BIM_EXTENSIONS)

    def list_output_files(self, project_name: str) -> list[VolumeFileInfo]:
        """List tool output files in 99_overige_documenten/bim-validator/.

        Args:
            project_name: Name of the project directory.

        Returns:
            List of VolumeFileInfo.
        """
        output_dir = self._root / project_name / OUTPUT_SUBDIR
        return self._list_files_in(output_dir)

    def get_file_path(
        self, project_name: str, filename: str, subdir: str = BIM_SUBDIR
    ) -> Path | None:
        """Get the absolute path to a file on the volume mount.

        Args:
            project_name: Project directory name.
            filename: File name.
            subdir: Subdirectory within the project (default: 70_BIM).

        Returns:
            Path if the file exists, None otherwise.
        """
        if not self.available:
            return None

        file_path = self._root / project_name / subdir / filename

        # Security: ensure path doesn't escape the project root
        try:
            file_path.resolve().relative_to(self._root.resolve())
        except ValueError:
            logger.warning("Path traversal attempt: %s", file_path)
            return None

        if file_path.is_file():
            return file_path
        return None

    def read_file(
        self, project_name: str, filename: str, subdir: str = BIM_SUBDIR
    ) -> bytes | None:
        """Read file content from the volume mount.

        Args:
            project_name: Project directory name.
            filename: File name.
            subdir: Subdirectory within the project.

        Returns:
            File bytes if found, None otherwise.
        """
        path = self.get_file_path(project_name, filename, subdir)
        if path is None:
            return None

        try:
            return path.read_bytes()
        except OSError as exc:
            logger.error("Failed to read %s: %s", path, exc)
            return None

    def project_exists(self, project_name: str) -> bool:
        """Check if a project directory exists."""
        if not self.available:
            return False
        return (self._root / project_name).is_dir()

    # ── Private helpers ────────────────────────────────────────

    def _list_files_in(
        self, directory: Path, extensions: set[str] | None = None
    ) -> list[VolumeFileInfo]:
        """List files in a directory, optionally filtered by extension."""
        if not directory.is_dir():
            return []

        files = []
        try:
            for entry in directory.iterdir():
                if not entry.is_file() or entry.name.startswith("."):
                    continue
                if extensions and entry.suffix.lower() not in extensions:
                    continue

                stat = entry.stat()
                modified = datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat()

                files.append(
                    VolumeFileInfo(
                        name=entry.name,
                        path=entry,
                        size=stat.st_size,
                        last_modified=modified,
                    )
                )
        except OSError as exc:
            logger.error("Failed to list %s: %s", directory, exc)
            return []

        files.sort(key=lambda f: f.name)
        return files
