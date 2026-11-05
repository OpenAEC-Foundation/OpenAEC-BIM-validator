"""Minimal thread-safe TTL job store for router-local async jobs.

Deliberately smaller than server.job_manager: routers that own their own
artifacts (result files on disk) register a cleanup callback so expiry
also removes those files. Cleanup runs opportunistically on every access,
mirroring the job-expiration behaviour of the validation endpoints.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

JOB_TTL_SECONDS = 30 * 60


@dataclass
class Job:
    """A single background job with its lifecycle state."""

    job_id: str
    status: str = "pending"  # pending | processing | completed | failed
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    artifacts: dict[str, Any] = field(default_factory=dict)


class JobStore:
    """Thread-safe in-memory job registry with TTL-based expiry."""

    def __init__(
        self,
        ttl_seconds: float = JOB_TTL_SECONDS,
        on_expire: Optional[Callable[[Job], None]] = None,
    ):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        self._on_expire = on_expire

    def create(self) -> Job:
        """Create and register a new pending job."""
        job = Job(job_id=str(uuid.uuid4()))
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        """Fetch a job by id, expiring stale jobs first."""
        self.cleanup_expired()
        with self._lock:
            return self._jobs.get(job_id)

    def start(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "processing"

    def complete(self, job_id: str, result: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "completed"
                job.result = result
                job.finished_at = time.time()

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "failed"
                job.error = error
                job.finished_at = time.time()

    def cleanup_expired(self) -> None:
        """Drop jobs older than the TTL, invoking the expiry callback."""
        now = time.time()
        expired: list[Job] = []
        with self._lock:
            for job_id, job in list(self._jobs.items()):
                if now - job.created_at > self._ttl:
                    expired.append(self._jobs.pop(job_id))
        if self._on_expire:
            for job in expired:
                try:
                    self._on_expire(job)
                except Exception:
                    pass
