"""BCF exports must obey the same retention policy as status responses."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from server.main import app, job_manager


def test_expired_bcf_cannot_be_downloaded_without_status_poll():
    job = job_manager.create_job()
    job_manager.complete_job(job.job_id, {"specifications": []})
    stored = job_manager.get_job(job.job_id)
    stored.completed_at = datetime.now(timezone.utc) - timedelta(
        seconds=job_manager._ttl_seconds + 1
    )
    try:
        response = TestClient(app).get(f"/api/v1/jobs/{job.job_id}/bcf")
        assert response.status_code == 404
    finally:
        job_manager._jobs.pop(job.job_id, None)
