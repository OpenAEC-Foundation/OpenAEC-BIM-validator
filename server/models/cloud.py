"""
Pydantic response models for the Nextcloud cloud storage API.

These models define the JSON shape of cloud storage endpoints.
"""

from pydantic import BaseModel, Field


class CloudStatusResponse(BaseModel):
    """Response for GET /api/cloud/status."""

    enabled: bool = Field(..., description="Whether cloud storage is configured")
    connected: bool = Field(
        False, description="Whether the Nextcloud instance is reachable"
    )


class CloudProjectItem(BaseModel):
    """A project folder in Nextcloud."""

    name: str = Field(..., description="Project folder name")
    last_modified: str = Field("", description="Last modification date")


class CloudFileItem(BaseModel):
    """A file in a project's tool subdirectory."""

    name: str = Field(..., description="File name")
    size: int = Field(0, description="File size in bytes")
    last_modified: str = Field("", description="Last modification date")


class CloudProjectsResponse(BaseModel):
    """Response for GET /api/cloud/projects."""

    projects: list[CloudProjectItem] = Field(
        default_factory=list, description="List of project folders"
    )


class CloudFilesResponse(BaseModel):
    """Response for GET /api/cloud/projects/{project}/files."""

    project: str = Field(..., description="Project name")
    files: list[CloudFileItem] = Field(
        default_factory=list, description="List of files in the project"
    )


class CloudUploadResponse(BaseModel):
    """Response for PUT /api/cloud/projects/{project}/files/{filename}."""

    success: bool = Field(..., description="Whether the upload succeeded")
    project: str = Field(..., description="Project name")
    filename: str = Field(..., description="Uploaded file name")


class CloudDeleteResponse(BaseModel):
    """Response for DELETE /api/cloud/projects/{project}/files/{filename}."""

    success: bool = Field(..., description="Whether the deletion succeeded")
    project: str = Field(..., description="Project name")
    filename: str = Field(..., description="Deleted file name")


class ManifestHeader(BaseModel):
    """Header section of a project.wefc manifest."""

    schema_name: str = Field(
        "WeFC", alias="schema", description="Schema identifier"
    )
    schema_version: str = Field(
        "1.0.0", description="Schema version"
    )
    timestamp: str = Field("", description="Last update timestamp (ISO 8601)")
    application: str = Field("", description="Application that last wrote")

    model_config = {"populate_by_name": True}


class ManifestResponse(BaseModel):
    """Response for GET /api/cloud/projects/{project}/manifest."""

    header: ManifestHeader = Field(
        default_factory=ManifestHeader,
        description="Manifest header",
    )
    data: list[dict] = Field(
        default_factory=list,
        description="List of WeFC objects in the project",
    )
