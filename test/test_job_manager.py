"""Unit tests for the server/job_manager.py module.

Tests cover:
- Job creation returns valid UUID
- Job retrieval works
- Job lifecycle transitions (pending->processing->completed/failed)
- Expiration cleanup works
- Concurrent job limits work
- Progress tracking

Usage:
    pytest test/test_job_manager.py -v
    pytest test/test_job_manager.py --cov=server --cov-report=term-missing
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.job_manager import (
    JobInfo,
    JobManager,
    JobStatus,
    JobStatusResponse,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def job_manager() -> JobManager:
    """Fresh JobManager instance for testing.

    Returns a new JobManager with default settings:
    - TTL: 3600 seconds (1 hour)
    - Max concurrent jobs: 10
    """
    return JobManager()


@pytest.fixture
def job_manager_short_ttl() -> JobManager:
    """JobManager with short TTL for expiration testing.

    Returns a JobManager with:
    - TTL: 1 second (for quick expiration tests)
    - Max concurrent jobs: 10
    """
    return JobManager(ttl_seconds=1)


@pytest.fixture
def job_manager_limited() -> JobManager:
    """JobManager with limited concurrent jobs for capacity testing.

    Returns a JobManager with:
    - TTL: 3600 seconds
    - Max concurrent jobs: 2 (for testing limits)
    """
    return JobManager(max_concurrent_jobs=2)


# =============================================================================
# Job Creation Tests
# =============================================================================


class TestJobCreation:
    """Test job creation functionality."""

    def test_create_job_returns_job_info(self, job_manager: JobManager) -> None:
        """Test that create_job returns a JobInfo instance.

        Acceptance Criteria:
        - create_job() returns JobInfo instance
        """
        job = job_manager.create_job()

        assert isinstance(job, JobInfo), (
            f"create_job() should return JobInfo, got {type(job).__name__}"
        )

    def test_create_job_returns_valid_uuid(self, job_manager: JobManager) -> None:
        """Test that created job has a valid UUID4 job_id.

        Acceptance Criteria:
        - job_id is a valid UUID4 string
        """
        job = job_manager.create_job()

        # Verify job_id is a non-empty string
        assert isinstance(job.job_id, str), (
            f"job_id should be str, got {type(job.job_id).__name__}"
        )
        assert len(job.job_id) > 0, "job_id should not be empty"

        # Verify it's a valid UUID by parsing it
        try:
            parsed_uuid = uuid.UUID(job.job_id)
            assert parsed_uuid is not None
        except ValueError as e:
            pytest.fail(f"job_id '{job.job_id}' is not a valid UUID: {e}")

        # Verify it's a UUID version 4
        assert parsed_uuid.version == 4, (
            f"job_id should be UUID4, got version {parsed_uuid.version}"
        )

    def test_create_job_initial_status_is_pending(self, job_manager: JobManager) -> None:
        """Test that new jobs have pending status.

        Acceptance Criteria:
        - New job status is PENDING
        """
        job = job_manager.create_job()

        assert job.status == JobStatus.PENDING, (
            f"New job status should be PENDING, got {job.status}"
        )

    def test_create_job_has_created_at_timestamp(self, job_manager: JobManager) -> None:
        """Test that new jobs have created_at timestamp.

        Acceptance Criteria:
        - created_at is a datetime in UTC
        - created_at is recent (within last minute)
        """
        before = datetime.now(timezone.utc)
        job = job_manager.create_job()
        after = datetime.now(timezone.utc)

        # Verify created_at is a datetime
        assert isinstance(job.created_at, datetime), (
            f"created_at should be datetime, got {type(job.created_at).__name__}"
        )

        # Verify created_at is within expected range
        assert before <= job.created_at <= after, (
            f"created_at {job.created_at} should be between {before} and {after}"
        )

    def test_create_job_optional_fields_are_none(self, job_manager: JobManager) -> None:
        """Test that new jobs have None for optional fields.

        Acceptance Criteria:
        - started_at is None
        - completed_at is None
        - result is None
        - error is None
        - progress is None
        """
        job = job_manager.create_job()

        assert job.started_at is None, "started_at should be None for new job"
        assert job.completed_at is None, "completed_at should be None for new job"
        assert job.result is None, "result should be None for new job"
        assert job.error is None, "error should be None for new job"
        assert job.progress is None, "progress should be None for new job"

    def test_create_multiple_jobs_unique_ids(self, job_manager: JobManager) -> None:
        """Test that multiple jobs have unique IDs.

        Acceptance Criteria:
        - Each created job has a unique job_id
        """
        num_jobs = 10
        jobs = [job_manager.create_job() for _ in range(num_jobs)]
        job_ids = [job.job_id for job in jobs]

        # Verify all IDs are unique
        assert len(set(job_ids)) == num_jobs, (
            f"Expected {num_jobs} unique job IDs, got {len(set(job_ids))}"
        )


# =============================================================================
# Job Retrieval Tests
# =============================================================================


class TestJobRetrieval:
    """Test job retrieval functionality."""

    def test_get_job_returns_created_job(self, job_manager: JobManager) -> None:
        """Test that get_job returns the correct job.

        Acceptance Criteria:
        - get_job(job_id) returns the job with matching ID
        """
        created_job = job_manager.create_job()
        retrieved_job = job_manager.get_job(created_job.job_id)

        assert retrieved_job is not None, "get_job should return the created job"
        assert retrieved_job.job_id == created_job.job_id, (
            f"Retrieved job_id {retrieved_job.job_id} should match "
            f"created job_id {created_job.job_id}"
        )

    def test_get_job_returns_none_for_unknown_id(self, job_manager: JobManager) -> None:
        """Test that get_job returns None for unknown job ID.

        Acceptance Criteria:
        - get_job(unknown_id) returns None
        """
        unknown_id = str(uuid.uuid4())
        result = job_manager.get_job(unknown_id)

        assert result is None, (
            f"get_job() should return None for unknown ID, got {result}"
        )

    def test_get_job_returns_job_info_instance(self, job_manager: JobManager) -> None:
        """Test that get_job returns a JobInfo instance.

        Acceptance Criteria:
        - get_job returns JobInfo (not dict or other type)
        """
        job = job_manager.create_job()
        retrieved = job_manager.get_job(job.job_id)

        assert isinstance(retrieved, JobInfo), (
            f"get_job should return JobInfo, got {type(retrieved).__name__}"
        )

    def test_get_job_preserves_all_fields(self, job_manager: JobManager) -> None:
        """Test that get_job preserves all job fields.

        Acceptance Criteria:
        - All fields from created job are preserved in retrieved job
        """
        job = job_manager.create_job()
        retrieved = job_manager.get_job(job.job_id)

        assert retrieved.job_id == job.job_id
        assert retrieved.status == job.status
        assert retrieved.created_at == job.created_at
        assert retrieved.started_at == job.started_at
        assert retrieved.completed_at == job.completed_at
        assert retrieved.result == job.result
        assert retrieved.error == job.error
        assert retrieved.progress == job.progress


# =============================================================================
# Job Lifecycle Tests
# =============================================================================


class TestJobLifecycle:
    """Test job lifecycle transitions."""

    def test_start_job_changes_status_to_processing(
        self, job_manager: JobManager
    ) -> None:
        """Test that start_job changes status to PROCESSING.

        Acceptance Criteria:
        - start_job() changes status from PENDING to PROCESSING
        """
        job = job_manager.create_job()
        assert job.status == JobStatus.PENDING

        updated_job = job_manager.start_job(job.job_id)

        assert updated_job is not None, "start_job should return updated job"
        assert updated_job.status == JobStatus.PROCESSING, (
            f"Status should be PROCESSING after start_job, got {updated_job.status}"
        )

    def test_start_job_sets_started_at_timestamp(
        self, job_manager: JobManager
    ) -> None:
        """Test that start_job sets started_at timestamp.

        Acceptance Criteria:
        - started_at is set to current time after start_job()
        """
        job = job_manager.create_job()
        assert job.started_at is None

        before = datetime.now(timezone.utc)
        updated_job = job_manager.start_job(job.job_id)
        after = datetime.now(timezone.utc)

        assert updated_job.started_at is not None, (
            "started_at should be set after start_job"
        )
        assert before <= updated_job.started_at <= after, (
            f"started_at {updated_job.started_at} should be between {before} and {after}"
        )

    def test_start_job_returns_none_for_unknown_id(
        self, job_manager: JobManager
    ) -> None:
        """Test that start_job returns None for unknown job ID.

        Acceptance Criteria:
        - start_job(unknown_id) returns None
        """
        unknown_id = str(uuid.uuid4())
        result = job_manager.start_job(unknown_id)

        assert result is None, "start_job should return None for unknown ID"

    def test_complete_job_changes_status_to_completed(
        self, job_manager: JobManager
    ) -> None:
        """Test that complete_job changes status to COMPLETED.

        Acceptance Criteria:
        - complete_job() changes status to COMPLETED
        - result is stored
        """
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        test_result = {"validation": "passed", "score": 100}
        updated_job = job_manager.complete_job(job.job_id, test_result)

        assert updated_job is not None, "complete_job should return updated job"
        assert updated_job.status == JobStatus.COMPLETED, (
            f"Status should be COMPLETED, got {updated_job.status}"
        )
        assert updated_job.result == test_result, (
            f"Result should be stored, got {updated_job.result}"
        )

    def test_complete_job_sets_completed_at_timestamp(
        self, job_manager: JobManager
    ) -> None:
        """Test that complete_job sets completed_at timestamp.

        Acceptance Criteria:
        - completed_at is set after complete_job()
        """
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        before = datetime.now(timezone.utc)
        updated_job = job_manager.complete_job(job.job_id, {"result": "test"})
        after = datetime.now(timezone.utc)

        assert updated_job.completed_at is not None, (
            "completed_at should be set after complete_job"
        )
        assert before <= updated_job.completed_at <= after

    def test_complete_job_returns_none_for_unknown_id(
        self, job_manager: JobManager
    ) -> None:
        """Test that complete_job returns None for unknown job ID.

        Acceptance Criteria:
        - complete_job(unknown_id, result) returns None
        """
        unknown_id = str(uuid.uuid4())
        result = job_manager.complete_job(unknown_id, {"test": "result"})

        assert result is None, "complete_job should return None for unknown ID"

    def test_fail_job_changes_status_to_failed(
        self, job_manager: JobManager
    ) -> None:
        """Test that fail_job changes status to FAILED.

        Acceptance Criteria:
        - fail_job() changes status to FAILED
        - error message is stored
        """
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        error_message = "Validation failed: Invalid IFC file"
        updated_job = job_manager.fail_job(job.job_id, error_message)

        assert updated_job is not None, "fail_job should return updated job"
        assert updated_job.status == JobStatus.FAILED, (
            f"Status should be FAILED, got {updated_job.status}"
        )
        assert updated_job.error == error_message, (
            f"Error message should be stored, got {updated_job.error}"
        )

    def test_fail_job_sets_completed_at_timestamp(
        self, job_manager: JobManager
    ) -> None:
        """Test that fail_job sets completed_at timestamp.

        Acceptance Criteria:
        - completed_at is set after fail_job()
        """
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        before = datetime.now(timezone.utc)
        updated_job = job_manager.fail_job(job.job_id, "Error occurred")
        after = datetime.now(timezone.utc)

        assert updated_job.completed_at is not None, (
            "completed_at should be set after fail_job"
        )
        assert before <= updated_job.completed_at <= after

    def test_fail_job_returns_none_for_unknown_id(
        self, job_manager: JobManager
    ) -> None:
        """Test that fail_job returns None for unknown job ID.

        Acceptance Criteria:
        - fail_job(unknown_id, error) returns None
        """
        unknown_id = str(uuid.uuid4())
        result = job_manager.fail_job(unknown_id, "Error message")

        assert result is None, "fail_job should return None for unknown ID"

    def test_full_lifecycle_pending_to_completed(
        self, job_manager: JobManager
    ) -> None:
        """Test full job lifecycle: pending -> processing -> completed.

        Acceptance Criteria:
        - Job transitions through all states correctly
        """
        # Create job - should be pending
        job = job_manager.create_job()
        assert job.status == JobStatus.PENDING

        # Start job - should be processing
        job_manager.start_job(job.job_id)
        job = job_manager.get_job(job.job_id)
        assert job.status == JobStatus.PROCESSING

        # Complete job - should be completed
        job_manager.complete_job(job.job_id, {"result": "success"})
        job = job_manager.get_job(job.job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.result == {"result": "success"}

    def test_full_lifecycle_pending_to_failed(
        self, job_manager: JobManager
    ) -> None:
        """Test full job lifecycle: pending -> processing -> failed.

        Acceptance Criteria:
        - Job transitions to failed state correctly
        """
        # Create job - should be pending
        job = job_manager.create_job()
        assert job.status == JobStatus.PENDING

        # Start job - should be processing
        job_manager.start_job(job.job_id)
        job = job_manager.get_job(job.job_id)
        assert job.status == JobStatus.PROCESSING

        # Fail job - should be failed
        job_manager.fail_job(job.job_id, "Something went wrong")
        job = job_manager.get_job(job.job_id)
        assert job.status == JobStatus.FAILED
        assert job.error == "Something went wrong"


# =============================================================================
# Job Update Tests
# =============================================================================


class TestJobUpdate:
    """Test generic job update functionality."""

    def test_update_job_modifies_fields(self, job_manager: JobManager) -> None:
        """Test that update_job can modify job fields.

        Acceptance Criteria:
        - update_job() modifies specified fields
        """
        job = job_manager.create_job()

        updated_job = job_manager.update_job(
            job.job_id,
            status=JobStatus.PROCESSING,
            progress="Processing step 1"
        )

        assert updated_job is not None
        assert updated_job.status == JobStatus.PROCESSING
        assert updated_job.progress == "Processing step 1"

    def test_update_job_returns_none_for_unknown_id(
        self, job_manager: JobManager
    ) -> None:
        """Test that update_job returns None for unknown job ID.

        Acceptance Criteria:
        - update_job(unknown_id, **kwargs) returns None
        """
        unknown_id = str(uuid.uuid4())
        result = job_manager.update_job(unknown_id, status=JobStatus.PROCESSING)

        assert result is None, "update_job should return None for unknown ID"

    def test_update_job_preserves_unmodified_fields(
        self, job_manager: JobManager
    ) -> None:
        """Test that update_job preserves fields not being updated.

        Acceptance Criteria:
        - Fields not in kwargs are preserved
        """
        job = job_manager.create_job()
        original_created_at = job.created_at

        updated_job = job_manager.update_job(job.job_id, progress="New progress")

        assert updated_job.created_at == original_created_at
        assert updated_job.status == JobStatus.PENDING  # Not changed
        assert updated_job.progress == "New progress"


# =============================================================================
# Progress Tracking Tests
# =============================================================================


class TestProgressTracking:
    """Test progress tracking functionality."""

    def test_update_progress_sets_progress_message(
        self, job_manager: JobManager
    ) -> None:
        """Test that update_progress sets the progress message.

        Acceptance Criteria:
        - update_progress() sets progress field
        """
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        progress_message = "Validating specification 3 of 13..."
        updated_job = job_manager.update_progress(job.job_id, progress_message)

        assert updated_job is not None
        assert updated_job.progress == progress_message

    def test_update_progress_can_update_multiple_times(
        self, job_manager: JobManager
    ) -> None:
        """Test that progress can be updated multiple times.

        Acceptance Criteria:
        - Progress can be overwritten with new values
        """
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        # Update progress multiple times
        job_manager.update_progress(job.job_id, "Step 1 of 5...")
        job_manager.update_progress(job.job_id, "Step 2 of 5...")
        updated_job = job_manager.update_progress(job.job_id, "Step 3 of 5...")

        assert updated_job.progress == "Step 3 of 5..."

    def test_update_progress_returns_none_for_unknown_id(
        self, job_manager: JobManager
    ) -> None:
        """Test that update_progress returns None for unknown job ID.

        Acceptance Criteria:
        - update_progress(unknown_id, message) returns None
        """
        unknown_id = str(uuid.uuid4())
        result = job_manager.update_progress(unknown_id, "Progress message")

        assert result is None, "update_progress should return None for unknown ID"


# =============================================================================
# Expiration Cleanup Tests
# =============================================================================


class TestExpirationCleanup:
    """Test job expiration and cleanup functionality."""

    def test_cleanup_expired_removes_old_completed_jobs(
        self, job_manager_short_ttl: JobManager
    ) -> None:
        """Test that cleanup_expired removes jobs older than TTL.

        Acceptance Criteria:
        - Jobs older than TTL are removed
        - Returns count of removed jobs
        """
        # Create and complete a job
        job = job_manager_short_ttl.create_job()
        job_manager_short_ttl.start_job(job.job_id)
        job_manager_short_ttl.complete_job(job.job_id, {"result": "test"})

        # Verify job exists
        assert job_manager_short_ttl.get_job(job.job_id) is not None

        # Mock time to simulate expiration
        future_time = datetime.now(timezone.utc) + timedelta(seconds=2)
        with patch("server.job_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            removed_count = job_manager_short_ttl.cleanup_expired()

        assert removed_count == 1, f"Should remove 1 job, removed {removed_count}"
        assert job_manager_short_ttl.get_job(job.job_id) is None, (
            "Expired job should be removed"
        )

    def test_cleanup_expired_removes_old_failed_jobs(
        self, job_manager_short_ttl: JobManager
    ) -> None:
        """Test that cleanup_expired removes failed jobs older than TTL.

        Acceptance Criteria:
        - Failed jobs older than TTL are removed
        """
        # Create and fail a job
        job = job_manager_short_ttl.create_job()
        job_manager_short_ttl.start_job(job.job_id)
        job_manager_short_ttl.fail_job(job.job_id, "Test error")

        # Mock time to simulate expiration
        future_time = datetime.now(timezone.utc) + timedelta(seconds=2)
        with patch("server.job_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            removed_count = job_manager_short_ttl.cleanup_expired()

        assert removed_count == 1
        assert job_manager_short_ttl.get_job(job.job_id) is None

    def test_cleanup_expired_removes_stuck_pending_jobs(
        self, job_manager_short_ttl: JobManager
    ) -> None:
        """Test that cleanup_expired removes stuck pending jobs.

        Acceptance Criteria:
        - Pending jobs older than TTL (stuck) are removed
        """
        # Create a job but don't start it
        job = job_manager_short_ttl.create_job()

        # Mock time to simulate expiration
        future_time = datetime.now(timezone.utc) + timedelta(seconds=2)
        with patch("server.job_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            removed_count = job_manager_short_ttl.cleanup_expired()

        assert removed_count == 1
        assert job_manager_short_ttl.get_job(job.job_id) is None

    def test_cleanup_expired_preserves_recent_jobs(
        self, job_manager: JobManager
    ) -> None:
        """Test that cleanup_expired does not remove recent jobs.

        Acceptance Criteria:
        - Jobs within TTL are preserved
        """
        # Create and complete a job
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)
        job_manager.complete_job(job.job_id, {"result": "test"})

        # Run cleanup immediately (job is still fresh)
        removed_count = job_manager.cleanup_expired()

        assert removed_count == 0, "Should not remove recent job"
        assert job_manager.get_job(job.job_id) is not None, (
            "Recent job should be preserved"
        )

    def test_cleanup_expired_returns_zero_for_no_expired_jobs(
        self, job_manager: JobManager
    ) -> None:
        """Test that cleanup_expired returns 0 when no jobs are expired.

        Acceptance Criteria:
        - Returns 0 when no jobs to clean up
        """
        # Create some fresh jobs
        job_manager.create_job()
        job_manager.create_job()

        removed_count = job_manager.cleanup_expired()

        assert removed_count == 0

    def test_cleanup_expired_with_empty_job_store(
        self, job_manager: JobManager
    ) -> None:
        """Test that cleanup_expired handles empty job store.

        Acceptance Criteria:
        - Returns 0 for empty store without error
        """
        removed_count = job_manager.cleanup_expired()

        assert removed_count == 0


# =============================================================================
# Concurrent Job Limit Tests
# =============================================================================


class TestConcurrentJobLimits:
    """Test concurrent job limits functionality."""

    def test_can_accept_job_returns_true_under_limit(
        self, job_manager_limited: JobManager
    ) -> None:
        """Test that can_accept_job returns True when under limit.

        Acceptance Criteria:
        - can_accept_job() returns True when active jobs < limit
        """
        # No jobs yet - should accept
        assert job_manager_limited.can_accept_job() is True

        # Create one pending job - should still accept
        job_manager_limited.create_job()
        assert job_manager_limited.can_accept_job() is True

    def test_can_accept_job_returns_false_at_limit(
        self, job_manager_limited: JobManager
    ) -> None:
        """Test that can_accept_job returns False when at limit.

        Acceptance Criteria:
        - can_accept_job() returns False when active jobs >= limit
        """
        # Create jobs up to limit (max_concurrent_jobs=2)
        job_manager_limited.create_job()
        job_manager_limited.create_job()

        # Should not accept more
        assert job_manager_limited.can_accept_job() is False

    def test_can_accept_job_counts_only_active_jobs(
        self, job_manager_limited: JobManager
    ) -> None:
        """Test that can_accept_job only counts pending/processing jobs.

        Acceptance Criteria:
        - Completed/failed jobs don't count toward limit
        """
        # Create and complete two jobs
        job1 = job_manager_limited.create_job()
        job2 = job_manager_limited.create_job()

        job_manager_limited.start_job(job1.job_id)
        job_manager_limited.complete_job(job1.job_id, {"result": "test"})

        job_manager_limited.start_job(job2.job_id)
        job_manager_limited.fail_job(job2.job_id, "Test error")

        # Both jobs are now completed/failed - should accept new jobs
        assert job_manager_limited.can_accept_job() is True

    def test_active_job_count_property(
        self, job_manager_limited: JobManager
    ) -> None:
        """Test active_job_count property returns correct count.

        Acceptance Criteria:
        - active_job_count counts pending and processing jobs
        """
        assert job_manager_limited.active_job_count == 0

        # Create pending job
        job1 = job_manager_limited.create_job()
        assert job_manager_limited.active_job_count == 1

        # Start it (now processing)
        job_manager_limited.start_job(job1.job_id)
        assert job_manager_limited.active_job_count == 1

        # Create another job
        job_manager_limited.create_job()
        assert job_manager_limited.active_job_count == 2

        # Complete first job
        job_manager_limited.complete_job(job1.job_id, {"result": "test"})
        assert job_manager_limited.active_job_count == 1

    def test_total_job_count_property(
        self, job_manager: JobManager
    ) -> None:
        """Test total_job_count property returns count of all jobs.

        Acceptance Criteria:
        - total_job_count includes all jobs regardless of status
        """
        assert job_manager.total_job_count == 0

        job1 = job_manager.create_job()
        assert job_manager.total_job_count == 1

        job2 = job_manager.create_job()
        job_manager.start_job(job2.job_id)
        job_manager.complete_job(job2.job_id, {"result": "test"})
        assert job_manager.total_job_count == 2

        job3 = job_manager.create_job()
        job_manager.start_job(job3.job_id)
        job_manager.fail_job(job3.job_id, "Error")
        assert job_manager.total_job_count == 3


# =============================================================================
# JobStatus Enum Tests
# =============================================================================


class TestJobStatusEnum:
    """Test JobStatus enum values and behavior."""

    def test_job_status_has_all_expected_values(self) -> None:
        """Test that JobStatus has all expected status values.

        Acceptance Criteria:
        - JobStatus has PENDING, PROCESSING, COMPLETED, FAILED
        """
        expected_statuses = ["pending", "processing", "completed", "failed"]

        for status in expected_statuses:
            assert hasattr(JobStatus, status.upper()), (
                f"JobStatus should have {status.upper()} value"
            )

    def test_job_status_values_are_strings(self) -> None:
        """Test that JobStatus values are lowercase strings.

        Acceptance Criteria:
        - Status values can be serialized as strings
        """
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"


# =============================================================================
# JobInfo Model Tests
# =============================================================================


class TestJobInfoModel:
    """Test JobInfo Pydantic model."""

    def test_job_info_required_fields(self) -> None:
        """Test that JobInfo requires job_id, status, and created_at.

        Acceptance Criteria:
        - JobInfo can be created with required fields
        """
        job = JobInfo(
            job_id="test-123",
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )

        assert job.job_id == "test-123"
        assert job.status == JobStatus.PENDING
        assert job.created_at is not None

    def test_job_info_optional_fields_default_to_none(self) -> None:
        """Test that JobInfo optional fields default to None.

        Acceptance Criteria:
        - Optional fields are None when not specified
        """
        job = JobInfo(
            job_id="test-123",
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )

        assert job.started_at is None
        assert job.completed_at is None
        assert job.result is None
        assert job.error is None
        assert job.progress is None

    def test_job_info_model_copy_creates_new_instance(self) -> None:
        """Test that model_copy creates independent copy.

        Acceptance Criteria:
        - model_copy() creates new instance with updated fields
        """
        original = JobInfo(
            job_id="test-123",
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )

        updated = original.model_copy(update={"status": JobStatus.PROCESSING})

        assert original.status == JobStatus.PENDING
        assert updated.status == JobStatus.PROCESSING
        assert original.job_id == updated.job_id


# =============================================================================
# JobStatusResponse Tests
# =============================================================================


class TestJobStatusResponse:
    """Test JobStatusResponse model and conversion."""

    def test_from_job_info_basic_fields(self) -> None:
        """Test that from_job_info converts basic fields correctly.

        Acceptance Criteria:
        - Basic fields are converted to response format
        """
        job = JobInfo(
            job_id="test-123",
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )

        response = JobStatusResponse.from_job_info(job)

        assert response.job_id == "test-123"
        assert response.status == "pending"
        assert response.created_at is not None

    def test_from_job_info_includes_progress_for_processing(self) -> None:
        """Test that from_job_info includes progress for processing jobs.

        Acceptance Criteria:
        - Progress field included when job has progress
        """
        job = JobInfo(
            job_id="test-123",
            status=JobStatus.PROCESSING,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            progress="Processing step 2 of 5..."
        )

        response = JobStatusResponse.from_job_info(job)

        assert response.progress == "Processing step 2 of 5..."

    def test_from_job_info_includes_result_for_completed(self) -> None:
        """Test that from_job_info includes result for completed jobs.

        Acceptance Criteria:
        - Result field included for completed jobs
        """
        start_time = datetime.now(timezone.utc)
        complete_time = start_time + timedelta(seconds=45)

        job = JobInfo(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            created_at=start_time,
            started_at=start_time,
            completed_at=complete_time,
            result={"validation": "passed"}
        )

        response = JobStatusResponse.from_job_info(job)

        assert response.result == {"validation": "passed"}
        assert response.duration_seconds is not None
        assert abs(response.duration_seconds - 45.0) < 0.1

    def test_from_job_info_includes_error_for_failed(self) -> None:
        """Test that from_job_info includes error for failed jobs.

        Acceptance Criteria:
        - Error field included for failed jobs
        """
        job = JobInfo(
            job_id="test-123",
            status=JobStatus.FAILED,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            error="Validation failed: Invalid IFC file"
        )

        response = JobStatusResponse.from_job_info(job)

        assert response.error == "Validation failed: Invalid IFC file"

    def test_from_job_info_datetime_formatting(self) -> None:
        """Test that datetime fields are formatted as ISO strings.

        Acceptance Criteria:
        - Datetime fields are converted to ISO 8601 strings
        """
        timestamp = datetime(2026, 1, 6, 12, 0, 0, tzinfo=timezone.utc)

        job = JobInfo(
            job_id="test-123",
            status=JobStatus.PENDING,
            created_at=timestamp
        )

        response = JobStatusResponse.from_job_info(job)

        # Should be ISO format string
        assert isinstance(response.created_at, str)
        assert "2026-01-06" in response.created_at


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_job_manager_custom_ttl(self) -> None:
        """Test JobManager with custom TTL.

        Acceptance Criteria:
        - Custom TTL is applied correctly
        """
        custom_ttl = 7200  # 2 hours
        manager = JobManager(ttl_seconds=custom_ttl)

        assert manager._ttl_seconds == custom_ttl

    def test_job_manager_custom_max_concurrent(self) -> None:
        """Test JobManager with custom max concurrent jobs.

        Acceptance Criteria:
        - Custom max concurrent jobs is applied correctly
        """
        custom_max = 5
        manager = JobManager(max_concurrent_jobs=custom_max)

        assert manager._max_concurrent_jobs == custom_max

    def test_complete_job_with_complex_result(
        self, job_manager: JobManager
    ) -> None:
        """Test completing job with complex nested result data.

        Acceptance Criteria:
        - Complex result data is stored correctly
        """
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        complex_result = {
            "summary": {
                "total_specifications": 12,
                "passed": 10,
                "failed": 2
            },
            "specifications": [
                {"name": "Spec 1", "passed": True, "failures": []},
                {"name": "Spec 2", "passed": False, "failures": [1, 2, 3]}
            ],
            "metadata": {
                "ifc_file": "test.ifc",
                "ids_file": "test.ids"
            }
        }

        updated_job = job_manager.complete_job(job.job_id, complex_result)

        assert updated_job.result == complex_result
        assert updated_job.result["summary"]["total_specifications"] == 12
        assert len(updated_job.result["specifications"]) == 2

    def test_fail_job_with_long_error_message(
        self, job_manager: JobManager
    ) -> None:
        """Test failing job with long error message.

        Acceptance Criteria:
        - Long error messages are stored correctly
        """
        job = job_manager.create_job()
        job_manager.start_job(job.job_id)

        long_error = "Error: " + "x" * 1000

        updated_job = job_manager.fail_job(job.job_id, long_error)

        assert updated_job.error == long_error
        assert len(updated_job.error) > 1000
