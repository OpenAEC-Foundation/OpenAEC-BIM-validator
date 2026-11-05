"""Test volume-backed project discovery, fallback and manifest reads."""

import json

import pytest

from server.tenant_config import TenantConfig
from server.volume_reader import VolumeReader


@pytest.fixture
def volume(tmp_path):
    config = TenantConfig(
        "test",
        "Test",
        "https://example.invalid",
        "example.invalid",
        "test",
        "",
        volume_mount=str(tmp_path),
    )
    config.projects_root.mkdir(parents=True)
    return config.projects_root, VolumeReader(config)


def write(root, relative, content=b"data"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_volume_discovery_filters_hidden_and_unrelated_files(volume):
    root, reader = volume
    write(root, "B/models/model.IFC")
    write(root, "A/models/rules.ids")
    write(root, "A/models/.hidden.ifc")
    write(root, "A/models/notes.txt")
    write(root, "A/models/directory/child.ifc")
    write(root, ".hidden/models/model.ifc")
    write(root, "readme.txt")
    assert reader.available
    assert [p.name for p in reader.list_projects()] == ["A", "B"]
    files = reader.list_bim_files("A")
    assert [f.name for f in files] == ["rules.ids"]
    assert files[0].size == 4
    assert files[0].last_modified
    assert reader.project_exists("A")
    assert not reader.project_exists("missing")


@pytest.mark.parametrize(
    "subdir,legacy",
    [("models", "70_BIM"), ("validation", "99_overige_documenten/bim-validator")],
)
def test_volume_reads_new_and_legacy_layouts(volume, subdir, legacy):
    root, reader = volume
    old = write(root, f"Project/{legacy}/model.ifc", b"legacy")
    listing = reader.list_bim_files if subdir == "models" else reader.list_output_files
    assert listing("Project")[0].path == old
    assert reader.read_file("Project", "model.ifc", subdir) == b"legacy"
    new = write(root, f"Project/{subdir}/model.ifc", b"current")
    assert listing("Project")[0].path == new
    assert reader.read_file("Project", "model.ifc", subdir) == b"current"
    assert reader.read_file("Project", "missing.ifc", subdir) is None
    assert reader.get_file_path("Project", "missing", "custom") is None
    assert reader.get_file_path("Project", "../../../../outside.ifc") is None


def test_manifest_discovery_and_invalid_content(volume):
    root, reader = volume
    data = {"header": {"schema": "WeFC"}}
    write(root, "Project/project.wefc", json.dumps(data).encode())
    write(root, "Project/invalid.wefc", b"not json")
    write(root, "Project/.hidden.wefc")
    write(root, "Project/other.txt")
    assert [m["name"] for m in reader.list_manifests("Project")] == [
        "invalid.wefc",
        "project.wefc",
    ]
    assert reader.read_manifest("Project") == data
    assert reader.read_manifest("Project", "invalid.wefc") is None
    assert reader.read_manifest("Project", "missing.wefc") is None
    assert reader.list_manifests("missing") == []
    outside = write(root.parent, "outside.wefc", b"{}")
    assert reader.read_manifest("Project", str(outside)) is None


def test_unavailable_volume_returns_fallback_values():
    reader = VolumeReader(TenantConfig("test", "Test", "", "", "", ""))
    assert not reader.available
    assert reader.list_projects() == []
    assert reader.list_manifests("Project") == []
    assert reader.read_manifest("Project") is None
    assert reader.read_file("Project", "model.ifc") is None
    assert not reader.project_exists("Project")


def test_volume_io_errors_allow_backend_fallback(volume, monkeypatch):
    root, reader = volume
    target = write(root, "Project/models/model.ifc")
    with monkeypatch.context() as patch:
        patch.setattr(
            type(target),
            "read_bytes",
            lambda _: (_ for _ in ()).throw(OSError("unavailable")),
        )
        assert reader.read_file("Project", "model.ifc") is None
    with monkeypatch.context() as patch:
        patch.setattr(
            type(root),
            "iterdir",
            lambda _: (_ for _ in ()).throw(OSError("unavailable")),
        )
        assert reader.list_projects() == []
        assert reader.list_bim_files("Project") == []
        assert reader.list_manifests("Project") == []
