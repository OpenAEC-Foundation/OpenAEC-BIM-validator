"""Tests for tenant-scoped project listing.

Verifies that ``GET /api/v2/projects`` only returns projects that match
the caller's tenant slug (resolved from the
``X-Authentik-Meta-Tenant`` forward-auth header). Complements the
scope-audit fix for Golf 5a B-6 — ``bim-validator`` list endpoint must
not leak projects across tenants.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine from a sync test context.

    ``asyncio.get_event_loop()`` without a running loop is deprecated
    in Python 3.12+ and raises ``RuntimeError`` in 3.14 — always create
    a fresh loop here.
    """
    return asyncio.new_event_loop().run_until_complete(coro)

# Ensure server package is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tenant_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[TestClient]:
    """FastAPI TestClient with a wiped ``projects`` table.

    Uses the default SQLite engine configured by ``server.database``
    (the engine must remain the original one so that the already-bound
    greenlet context keeps working with the conftest-level import of
    ``server.main``). The ``projects`` + ``project_files`` tables are
    created (in case ``init_db`` has not run yet) and then truncated
    before the test body runs, guaranteeing isolation without touching
    the engine itself.
    """
    from server.database import Base, engine  # noqa: WPS433
    from server.models.db_models import Project, ProjectFile  # noqa: WPS433,F401

    files_dir = tmp_path / "files"
    files_dir.mkdir()
    monkeypatch.setenv("PROJECT_FILES_DIR", str(files_dir))

    async def _reset_schema() -> None:
        async with engine.begin() as conn:
            # Create all tables (no-op if already present), then wipe
            # the two tables this test exercises.
            await conn.run_sync(Base.metadata.create_all)
            await conn.exec_driver_sql("DELETE FROM project_files")
            await conn.exec_driver_sql("DELETE FROM projects")

    _run_async(_reset_schema())

    from server.main import app  # noqa: WPS433

    with TestClient(app) as client:
        yield client


def _auth_headers(username: str, tenant: str) -> dict[str, str]:
    """Build Authentik forward-auth headers for a user in a tenant."""
    return {
        "X-authentik-username": username,
        "X-Authentik-Meta-Tenant": tenant,
    }


def _seed_project(name: str, tenant: str | None) -> None:
    """Insert a project row directly via SQLAlchemy, bypassing HTTP.

    The POST endpoint's ``project.to_dict()`` triggers a selectin-lazy
    load of ``project.files`` on the freshly-flushed row, which fails
    under ``TestClient`` + async SQLAlchemy with a ``MissingGreenlet``
    because the response serialisation happens outside the greenlet
    context. This is a pre-existing issue in the endpoint, unrelated
    to tenant scoping, so the tests seed via the ORM directly to keep
    the scope narrow.
    """
    from server.database import get_session  # noqa: WPS433
    from server.models.db_models import Project  # noqa: WPS433

    async def _insert() -> None:
        async with get_session() as session:
            session.add(Project(name=name, tenant=tenant))

    _run_async(_insert())


class TestProjectListTenantIsolation:
    """GET /api/v2/projects filters by the caller's tenant."""

    def test_list_excludes_other_tenant_projects(
        self, tenant_client: TestClient
    ) -> None:
        """A project owned by tenant A must not appear for tenant B."""
        _seed_project("Project A", "tenant-a")
        _seed_project("Project B", "tenant-b")

        # Tenant A lists: only sees own project
        list_a = tenant_client.get(
            "/api/v2/projects",
            headers=_auth_headers("alice", "tenant-a"),
        )
        assert list_a.status_code == 200
        names_a = {p["name"] for p in list_a.json()["projects"]}
        assert names_a == {"Project A"}

        # Tenant B lists: only sees own project
        list_b = tenant_client.get(
            "/api/v2/projects",
            headers=_auth_headers("bob", "tenant-b"),
        )
        assert list_b.status_code == 200
        names_b = {p["name"] for p in list_b.json()["projects"]}
        assert names_b == {"Project B"}

    def test_list_without_auth_header_returns_all(
        self, tenant_client: TestClient
    ) -> None:
        """Local/dev calls without forward-auth still see every project.

        This preserves backward compatibility for environments where
        Authentik is not in front of the service (the header-less
        default pathway).
        """
        _seed_project("Project A", "tenant-a")
        _seed_project("Project B", "tenant-b")

        resp = tenant_client.get("/api/v2/projects")
        assert resp.status_code == 200
        names = {p["name"] for p in resp.json()["projects"]}
        assert names == {"Project A", "Project B"}

    def test_legacy_null_tenant_hidden_from_scoped_view(
        self, tenant_client: TestClient
    ) -> None:
        """Legacy rows with NULL tenant do not leak into a scoped listing.

        When ``tenant IS NULL`` (pre-migration data), a tenant-scoped
        caller must not see the row. The fix is fail-closed.
        """
        _seed_project("Legacy project", None)

        # Scoped caller: does NOT see it
        resp = tenant_client.get(
            "/api/v2/projects",
            headers=_auth_headers("alice", "tenant-a"),
        )
        assert resp.status_code == 200
        names = {p["name"] for p in resp.json()["projects"]}
        assert "Legacy project" not in names

        # Unauthenticated caller (no header): sees it (backward compat)
        resp_open = tenant_client.get("/api/v2/projects")
        assert resp_open.status_code == 200
        names_open = {p["name"] for p in resp_open.json()["projects"]}
        assert "Legacy project" in names_open

    def test_list_response_exposes_tenant_field(
        self, tenant_client: TestClient
    ) -> None:
        """``to_summary()`` now surfaces the tenant slug so UIs can show it."""
        _seed_project("Owned project", "tenant-a")

        resp = tenant_client.get(
            "/api/v2/projects",
            headers=_auth_headers("alice", "tenant-a"),
        )
        assert resp.status_code == 200
        rows = resp.json()["projects"]
        assert len(rows) == 1
        assert rows[0]["tenant"] == "tenant-a"
