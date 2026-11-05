"""Verify installed desktop storage is writable per user."""

import os
import runpy
import sys
from pathlib import Path


def test_frozen_server_stores_projects_beside_user_database(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PROJECT_FILES_DIR", raising=False)
    entry = Path(__file__).parents[1] / "installer" / "server_headless.py"
    runpy.run_path(str(entry), run_name="desktop_bootstrap_test")
    expected = tmp_path / "BIMValidator"
    assert expected.is_dir()
    assert (
        os.environ["DATABASE_URL"]
        == f"sqlite+aiosqlite:///{expected / 'bimvalidator.db'}"
    )
    assert Path(os.environ["PROJECT_FILES_DIR"]) == expected / "projects"


def test_frozen_server_preserves_explicit_storage_config(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///custom.db")
    monkeypatch.setenv("PROJECT_FILES_DIR", str(tmp_path / "custom"))
    entry = Path(__file__).parents[1] / "installer" / "server_headless.py"
    runpy.run_path(str(entry), run_name="desktop_bootstrap_test")
    assert os.environ["DATABASE_URL"] == "sqlite+aiosqlite:///custom.db"
    assert Path(os.environ["PROJECT_FILES_DIR"]) == tmp_path / "custom"
