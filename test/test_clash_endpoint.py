"""Endpoint tests for /api/v1/clash (async clash-detection jobs)."""

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


def _file(field, name="sample.ifc"):
    content = (FIXTURES / "sample.ifc").read_bytes()
    return (field, (name, io.BytesIO(content), "application/octet-stream"))


def test_clash_single_model_flow(client):
    resp = client.post("/api/v1/clash", files=[_file("ifc_a")])
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    body = client.get(f"/api/v1/clash/jobs/{job_id}").json()
    assert body["status"] in ("completed", "failed"), body
    if body["status"] == "completed":
        result = body["result"]
        assert result["mode"] == "intersection"
        assert isinstance(result["clashes"], list)
        assert result["clash_count"] == len(result["clashes"]) + result[
            "results_omitted"
        ]


def test_clash_two_models(client):
    resp = client.post(
        "/api/v1/clash",
        files=[_file("ifc_a", "a.ifc"), _file("ifc_b", "b.ifc")],
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    body = client.get(f"/api/v1/clash/jobs/{job_id}").json()
    assert body["status"] in ("completed", "failed"), body


def test_clash_unknown_mode_rejected(client):
    resp = client.post(
        "/api/v1/clash", files=[_file("ifc_a")], data={"mode": "bogus"}
    )
    assert resp.status_code == 422


def test_clash_wrong_extension_rejected(client):
    files = [("ifc_a", ("x.txt", io.BytesIO(b"nope"), "text/plain"))]
    resp = client.post("/api/v1/clash", files=files)
    assert resp.status_code == 400


def test_clash_unknown_job_404(client):
    resp = client.get("/api/v1/clash/jobs/does-not-exist")
    assert resp.status_code == 404


def test_status_probe_reports_capabilities(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "clash" in body["capabilities"]
    assert "optimize" in body["capabilities"]
