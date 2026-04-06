"""
Direct filesystem reader for Nextcloud volume mounts.

Reads project listings and file contents directly from the read-only
Nextcloud data volume, bypassing WebDAV for fast I/O on large files.

Falls back to None/empty when volume mount is not available,
so callers can use WebDAV as fallback.

Supports the new project container model (models/, validation/) with
backward compatibility for legacy paths (70_BIM, 99_overige_documenten).
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.tenant_config import TenantConfig

logger = logging.getLogger(__name__)

TOOL_SLUG = "bim-validator"

# ── New project container model paths ──────────────────────────
DIR_MODELS = "models"
DIR_VALIDATION = "validation"
MANIFEST_FILENAME = "project.wefc"

# ── Legacy paths (backward compatibility) ──────────────────────
LEGACY_BIM_SUBDIR = "70_BIM"
LEGACY_OUTPUT_SUBDIR = f"99_overige_documenten/{TOOL_SLUG}"

# Keep old names as aliases for import compatibility
BIM_SUBDIR = LEGACY_BIM_SUBDIR
OUTPUT_SUBDIR = LEGACY_OUTPUT_SUBDIR

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
        """List BIM model files (IFC/IDS/BCF).

        Tries new models/ directory first, falls back to legacy 70_BIM/.

        Args:
            project_name: Name of the project directory.

        Returns:
            List of VolumeFileInfo for matching files.
        """
        # Try new path first
        new_dir = self._root / project_name / DIR_MODELS
        files = self._list_files_in(new_dir, BIM_EXTENSIONS)
        if files:
            return files
        # Fallback to legacy path
        legacy_dir = self._root / project_name / LEGACY_BIM_SUBDIR
        return self._list_files_in(legacy_dir, BIM_EXTENSIONS)

    def list_output_files(
        self, project_name: str
    ) -> list[VolumeFileInfo]:
        """List validation output files.

        Tries new validation/ directory first, falls back to legacy
        99_overige_documenten/bim-validator/.

        Args:
            project_name: Name of the project directory.

        Returns:
            List of VolumeFileInfo.
        """
        # Try new path first
        new_dir = self._root / project_name / DIR_VALIDATION
        files = self._list_files_in(new_dir)
        if files:
            return files
        # Fallback to legacy path
        legacy_dir = self._root / project_name / LEGACY_OUTPUT_SUBDIR
        return self._list_files_in(legacy_dir)

    def get_file_path(
        self,
        project_name: str,
        filename: str,
        subdir: str = DIR_MODELS,
    ) -> Path | None:
        """Get the absolute path to a file on the volume mount.

        Checks the given subdir first. For model and validation
        subdirs, falls back to legacy paths automatically.

        Args:
            project_name: Project directory name.
            filename: File name.
            subdir: Subdirectory within the project (default: models).

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

        # Fallback to legacy paths
        fallback_subdir = self._legacy_fallback(subdir)
        if fallback_subdir and fallback_subdir != subdir:
            fallback_path = (
                self._root / project_name / fallback_subdir / filename
            )
            try:
                fallback_path.resolve().relative_to(
                    self._root.resolve()
                )
            except ValueError:
                return None
            if fallback_path.is_file():
                return fallback_path

        return None

    def read_file(
        self,
        project_name: str,
        filename: str,
        subdir: str = DIR_MODELS,
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

    def read_manifest(
        self, project_name: str
    ) -> dict[str, Any] | None:
        """Read and parse the project.wefc manifest from volume.

        Args:
            project_name: Name of the project directory.

        Returns:
            Parsed manifest dict, or None if not found/invalid.
        """
        if not self.available:
            return None

        manifest_path = (
            self._root / project_name / MANIFEST_FILENAME
        )
        if not manifest_path.is_file():
            return None

        try:
            content = manifest_path.read_text(encoding="utf-8")
            return json.loads(content)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Manifest read error for %s: %s",
                project_name,
                exc,
            )
            return None

    def project_exists(self, project_name: str) -> bool:
        """Check if a project directory exists."""
        if not self.available:
            return False
        return (self._root / project_name).is_dir()

    # ── Private helpers ────────────────────────────────────────

    @staticmethod
    def _legacy_fallback(subdir: str) -> str | None:
        """Map a new-style subdir to its legacy equivalent.

        Args:
            subdir: New-style subdirectory name.

        Returns:
            Legacy subdirectory path, or None if no mapping exists.
        """
        mapping = {
            DIR_MODELS: LEGACY_BIM_SUBDIR,
            DIR_VALIDATION: LEGACY_OUTPUT_SUBDIR,
        }
        return mapping.get(subdir)

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
