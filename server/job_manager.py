"""
Job manager for async validation tasks.

This module provides job state management for background validation tasks.
Jobs are tracked in-memory with auto-cleanup of expired jobs after TTL.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    """Status of a validation job.

    Represents the lifecycle states of an async validation job,
    from initial queue to final completion or failure.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobInfo(BaseModel):
    """Information about a validation job.

    Contains all metadata and results for an async validation job,
    including timing information and validation results when complete.
    """

    job_id: str = Field(..., description="Unique identifier for the job (UUID4)")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Timestamp when job was created")
    started_at: Optional[datetime] = Field(
        None, description="Timestamp when processing started"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Timestamp when job completed or failed"
    )
    result: Optional[Any] = Field(
        None, description="Validation result when completed (ValidationResult)"
    )
    error: Optional[str] = Field(
        None, description="Error message if job failed"
    )
    progress: Optional[str] = Field(
        None, description="Progress message during processing"
    )

    model_config = ConfigDict(use_enum_values=True)


class JobStatusResponse(BaseModel):
    """API response model for job status endpoint.

    Provides type-safe response formatting for job status queries.
    Different fields are populated based on job status:
    - pending/processing: includes progress field
    - completed: includes result and duration_seconds
    - failed: includes error message

    All datetime fields are serialized to ISO 8601 format strings.
    """

    job_id: str = Field(
        ...,
        description="Unique identifier for the job (UUID4)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    status: str = Field(
        ...,
        description="Current job status: pending, processing, completed, or failed",
        examples=["pending", "processing", "completed", "failed"],
    )
    created_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when job was created",
        examples=["2026-01-06T12:00:00+00:00"],
    )
    started_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when processing started",
        examples=["2026-01-06T12:00:01+00:00"],
    )
    completed_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when job completed or failed",
        examples=["2026-01-06T12:00:45+00:00"],
    )
    progress: Optional[str] = Field(
        None,
        description="Progress message (for pending/processing jobs)",
        examples=["Validating IFC against IDS specification..."],
    )
    result: Optional[Any] = Field(
        None,
        description="Validation result containing ValidationReport (for completed jobs)",
    )
    error: Optional[str] = Field(
        None,
        description="Error message (for failed jobs)",
        examples=["Invalid IDS file: XML parsing error"],
    )
    duration_seconds: Optional[float] = Field(
        None,
        description="Processing duration in seconds (for completed jobs)",
        examples=[44.5],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "pending",
                    "created_at": "2026-01-06T12:00:00+00:00",
                },
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "processing",
                    "created_at": "2026-01-06T12:00:00+00:00",
                    "started_at": "2026-01-06T12:00:01+00:00",
                    "progress": "Validating IFC against IDS specification...",
                },
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "completed",
                    "created_at": "2026-01-06T12:00:00+00:00",
                    "started_at": "2026-01-06T12:00:01+00:00",
                    "completed_at": "2026-01-06T12:00:45+00:00",
                    "duration_seconds": 44.0,
                    "result": {
                        "success": True,
                        "ifc_filename": "model.ifc",
                        "ids_filename": "requirements.ids",
                        "total_specifications": 5,
                        "passed_specifications": 4,
                        "failed_specifications": 1,
                        "pass_rate_percent": 80.0,
                    },
                },
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "failed",
                    "created_at": "2026-01-06T12:00:00+00:00",
                    "started_at": "2026-01-06T12:00:01+00:00",
                    "completed_at": "2026-01-06T12:00:02+00:00",
                    "duration_seconds": 1.0,
                    "error": "Invalid IDS file: XML parsing error",
                },
            ]
        }
    )

    @classmethod
    def from_job_info(cls, job: "JobInfo") -> "JobStatusResponse":
        """Create a JobStatusResponse from a JobInfo instance.

        Formats the response based on job status:
        - pending/processing: includes progress if available
        - completed: includes result and duration_seconds
        - failed: includes error message

        Args:
            job: JobInfo instance to convert

        Returns:
            Formatted JobStatusResponse
        """
        # Base fields always included
        response_data = {
            "job_id": job.job_id,
            "status": job.status if isinstance(job.status, str) else job.status.value,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

        # Include progress for pending/processing jobs
        if job.progress:
            response_data["progress"] = job.progress

        # Include result for completed jobs
        if job.result is not None:
            response_data["result"] = job.result

        # Include error for failed jobs
        if job.error:
            response_data["error"] = job.error

        # Calculate duration for completed jobs
        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            response_data["duration_seconds"] = round(duration, 2)

        return cls(**response_data)


class JobManager:
    """Manager for async validation jobs.

    Handles job creation, status tracking, lifecycle management,
    and automatic cleanup of expired jobs. Uses in-memory storage
    suitable for single-server MVP deployments.
    """

    def __init__(self, ttl_seconds: int = 3600, max_concurrent_jobs: int = 10) -> None:
        """Initialize the job manager.

        Args:
            ttl_seconds: Time-to-live for completed jobs in seconds (default: 1 hour)
            max_concurrent_jobs: Maximum number of concurrent jobs allowed
        """
        self._jobs: dict[str, JobInfo] = {}
        self._ttl_seconds = ttl_seconds
        self._max_concurrent_jobs = max_concurrent_jobs

    def create_job(
        self,
        job_id: Optional[str] = None,
        ifc_filename: Optional[str] = None,
        ids_filename: Optional[str] = None,
    ) -> JobInfo:
        """Create a new job with pending status.

        Generates a new UUID4 job_id (or uses provided one) and initializes
        the job with pending status and current timestamp.

        Args:
            job_id: Optional job ID (generates UUID4 if not provided)
            ifc_filename: Optional IFC filename for metadata
            ids_filename: Optional IDS filename for metadata

        Returns:
            The created JobInfo instance
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        job = JobInfo(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Retrieve a job by its ID.

        Args:
            job_id: Unique identifier of the job

        Returns:
            JobInfo if found, None otherwise
        """
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs: Any) -> Optional[JobInfo]:
        """Update job fields.

        Args:
            job_id: Unique identifier of the job
            **kwargs: Fields to update on the job

        Returns:
            Updated JobInfo if found, None otherwise
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None
        updated_job = job.model_copy(update=kwargs)
        self._jobs[job_id] = updated_job
        return updated_job

    def start_job(self, job_id: str) -> Optional[JobInfo]:
        """Mark a job as processing.

        Sets the job status to PROCESSING and records the started_at timestamp.

        Args:
            job_id: Unique identifier of the job

        Returns:
            Updated JobInfo if found, None otherwise
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None
        updated_job = job.model_copy(
            update={
                "status": JobStatus.PROCESSING,
                "started_at": datetime.now(timezone.utc),
            }
        )
        self._jobs[job_id] = updated_job
        return updated_job

    def complete_job(self, job_id: str, result: Any) -> Optional[JobInfo]:
        """Mark a job as completed with result.

        Sets the job status to COMPLETED, stores the validation result,
        and records the completed_at timestamp.

        Args:
            job_id: Unique identifier of the job
            result: Validation result data

        Returns:
            Updated JobInfo if found, None otherwise
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None
        updated_job = job.model_copy(
            update={
                "status": JobStatus.COMPLETED,
                "result": result,
                "completed_at": datetime.now(timezone.utc),
            }
        )
        self._jobs[job_id] = updated_job
        return updated_job

    def fail_job(self, job_id: str, error: str) -> Optional[JobInfo]:
        """Mark a job as failed with error message.

        Sets the job status to FAILED, stores the error message,
        and records the completed_at timestamp.

        Args:
            job_id: Unique identifier of the job
            error: Error message describing the failure

        Returns:
            Updated JobInfo if found, None otherwise
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None
        updated_job = job.model_copy(
            update={
                "status": JobStatus.FAILED,
                "error": error,
                "completed_at": datetime.now(timezone.utc),
            }
        )
        self._jobs[job_id] = updated_job
        return updated_job

    def update_progress(self, job_id: str, progress: str) -> Optional[JobInfo]:
        """Update the progress message for a job.

        Sets the progress message for a job, typically used during processing
        to indicate current status like 'Validating specification 3 of 13...'.

        Args:
            job_id: Unique identifier of the job
            progress: Progress message to display

        Returns:
            Updated JobInfo if found, None otherwise
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None
        updated_job = job.model_copy(update={"progress": progress})
        self._jobs[job_id] = updated_job
        return updated_job

    def cleanup_expired(self) -> int:
        """Remove jobs older than TTL.

        Removes jobs that have been completed or failed for longer than the TTL,
        or pending/processing jobs that were created longer than TTL ago
        (stuck jobs).

        Returns:
            Number of jobs removed
        """
        now = datetime.now(timezone.utc)
        expired_job_ids: list[str] = []

        for job_id, job in self._jobs.items():
            # For completed/failed jobs, use completed_at
            # For pending/processing jobs, use created_at (stuck jobs)
            if job.completed_at is not None:
                age_seconds = (now - job.completed_at).total_seconds()
            else:
                age_seconds = (now - job.created_at).total_seconds()

            if age_seconds >= self._ttl_seconds:
                expired_job_ids.append(job_id)

        for job_id in expired_job_ids:
            del self._jobs[job_id]

        return len(expired_job_ids)

    def can_accept_job(self) -> bool:
        """Check if a new job can be accepted.

        Checks whether the number of active (pending or processing) jobs
        is below the maximum concurrent jobs limit.

        Returns:
            True if under the concurrent job limit, False otherwise
        """
        return self.active_job_count < self._max_concurrent_jobs

    @property
    def active_job_count(self) -> int:
        """Get count of active (pending or processing) jobs.

        Returns:
            Number of active jobs
        """
        return sum(
            1
            for job in self._jobs.values()
            if job.status in (JobStatus.PENDING, JobStatus.PROCESSING)
        )

    @property
    def total_job_count(self) -> int:
        """Get total count of all tracked jobs.

        Returns:
            Total number of jobs
        """
        return len(self._jobs)
