"""Endpoint tests for /api/v1/optimize (async optimizer jobs)."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _upload(name="sample.ifc"):
    content = (FIXTURES / "sample.ifc").read_bytes()
    return {"ifc_file": (name, io.BytesIO(content), "application/octet-stream")}


def test_list_passes(client):
    resp = client.get("/api/v1/optimize/passes")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["passes"]]
    assert "fix_duplicate_globalids" in names
    assert "compact" in names


def test_optimize_job_full_flow(client):
    resp = client.post("/api/v1/optimize", files=_upload())
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # TestClient runs background tasks synchronously after the response
    status = client.get(f"/api/v1/optimize/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed", body
    report = body["report"]
    assert report["input_file"] == "sample.ifc"
    assert report["size_before"] > 0
    assert report["size_after"] > 0
    assert len(report["passes"]) == 4

    download = client.get(f"/api/v1/optimize/jobs/{job_id}/download")
    assert download.status_code == 200
    assert b"ISO-10303-21" in download.content[:100]


def test_optimize_subset_passes(client):
    resp = client.post(
        "/api/v1/optimize",
        files=_upload(),
        data={"passes": "fix_duplicate_globalids,remove_unused_psets"},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    body = client.get(f"/api/v1/optimize/jobs/{job_id}").json()
    assert body["status"] == "completed"
    names = [p["name"] for p in body["report"]["passes"]]
    assert names == ["fix_duplicate_globalids", "remove_unused_psets"]


def test_optimize_unknown_pass_rejected(client):
    resp = client.post(
        "/api/v1/optimize", files=_upload(), data={"passes": "bogus"}
    )
    assert resp.status_code == 422
    assert "bogus" in resp.json()["detail"]


def test_optimize_wrong_extension_rejected(client):
    files = {"ifc_file": ("x.txt", io.BytesIO(b"nope"), "text/plain")}
    resp = client.post("/api/v1/optimize", files=files)
    assert resp.status_code == 400


def test_optimize_unknown_job_404(client):
    resp = client.get("/api/v1/optimize/jobs/does-not-exist")
    assert resp.status_code == 404
