"""
SQLAlchemy ORM models for projects and project files.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    """A BIM validation project containing IFC/BCF/IDS files."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    files: Mapped[list["ProjectFile"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "files": [f.to_dict() for f in self.files],
        }

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "fileCount": len(self.files),
        }


class ProjectFile(Base):
    """A file (IFC, BCF, or IDS) belonging to a project."""

    __tablename__ = "project_files"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    file_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # 'ifc', 'bcf', 'ids'
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    disk_path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="files")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "fileType": self.file_type,
            "fileName": self.file_name,
            "fileSize": self.file_size,
            "uploadedAt": self.uploaded_at.isoformat(),
            "metadata": self.metadata_json,
        }
