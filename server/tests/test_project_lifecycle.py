"""Exercise persistent projects through their public HTTP lifecycle."""

import pytest

from server.routers import projects
from server.tests.test_projects_tenant import tenant_client  # noqa: F401


@pytest.fixture
def project_client(request, monkeypatch, tmp_path):
    monkeypatch.setattr(projects, "PROJECT_FILES_DIR", tmp_path / "projects")
    return request.getfixturevalue("tenant_client")


def test_project_create_update_delete(project_client):
    created = project_client.post("/api/v2/projects", data={"name": "Model review"})
    assert created.status_code == 201
    project = created.json()
    assert project["files"] == []
    url = f"/api/v2/projects/{project['id']}"
    updated = project_client.put(url, data={"name": "Reviewed", "description": "Ready"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Reviewed"
    assert project_client.get(url).json()["description"] == "Ready"
    assert project_client.delete(url).status_code == 200
    assert project_client.get(url).status_code == 404
    assert not (projects.PROJECT_FILES_DIR / project["id"]).exists()


@pytest.mark.parametrize(
    "filename", ["model.ifc", "../model.ifc", "..\\model.ifc", "x" * 300 + ".ifc"]
)
def test_project_file_roundtrip_uses_bounded_storage_name(project_client, filename):
    created = project_client.post("/api/v2/projects", data={"name": "Files"})
    assert created.status_code == 201
    project_id = created.json()["id"]
    url = f"/api/v2/projects/{project_id}/files"
    uploaded = project_client.post(
        url, data={"file_type": "ifc"}, files={"file": (filename, b"model content")}
    )
    assert uploaded.status_code == 201
    file = uploaded.json()
    assert file["fileName"] == filename
    files = list((projects.PROJECT_FILES_DIR / project_id / "ifc").iterdir())
    assert len(files) == 1
    assert len(files[0].name) == 36
    assert project_client.get(url).json()["files"][0]["id"] == file["id"]
    assert project_client.get(url, params={"file_type": "ids"}).json()["files"] == []
    download_url = f"{url}/{file['id']}"
    assert project_client.get(download_url).content == b"model content"
    assert project_client.delete(download_url).status_code == 200
    assert project_client.get(download_url).status_code == 404
    assert not files[0].exists()
