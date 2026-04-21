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
from unittest.mock import MagicMock, patch

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


def _seed_project(name: str, tenant: str | None) -> str:
    """Insert a project row directly via SQLAlchemy, bypassing HTTP.

    The POST endpoint's ``project.to_dict()`` triggers a selectin-lazy
    load of ``project.files`` on the freshly-flushed row, which fails
    under ``TestClient`` + async SQLAlchemy with a ``MissingGreenlet``
    because the response serialisation happens outside the greenlet
    context. This is a pre-existing issue in the endpoint, unrelated
    to tenant scoping, so the tests seed via the ORM directly to keep
    the scope narrow.

    Returns the generated project id so per-project cross-tenant tests
    can target a specific row.
    """
    from server.database import get_session  # noqa: WPS433
    from server.models.db_models import Project  # noqa: WPS433

    holder: dict[str, str] = {}

    async def _insert() -> None:
        async with get_session() as session:
            project = Project(name=name, tenant=tenant)
            session.add(project)
            await session.flush()
            holder["id"] = project.id

    _run_async(_insert())
    return holder["id"]


def _seed_project_file(project_id: str, file_type: str, file_name: str) -> str:
    """Insert a ProjectFile row for ``project_id`` via the ORM.

    Only creates the DB row — no disk file. Tests that verify tenant
    isolation on file endpoints check that the 404 short-circuit fires
    before any disk access, so a physical file is not needed.
    """
    from server.database import get_session  # noqa: WPS433
    from server.models.db_models import ProjectFile  # noqa: WPS433

    holder: dict[str, str] = {}

    async def _insert() -> None:
        async with get_session() as session:
            file_row = ProjectFile(
                project_id=project_id,
                file_type=file_type,
                file_name=file_name,
                file_size=0,
                disk_path=f"{project_id}/{file_type}/{file_name}",
            )
            session.add(file_row)
            await session.flush()
            holder["id"] = file_row.id

    _run_async(_insert())
    return holder["id"]


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


class TestProjectDetailTenantIsolation:
    """Per-project endpoints enforce tenant scoping via ``_get_project_for_tenant``.

    All endpoints that accept ``{project_id}`` must return ``404`` (not
    ``403``) when the caller's tenant does not match the project row.
    ``404`` is deliberate: ``403`` would disclose that the id exists in
    another tenant. Complements the scope-audit follow-up on the
    Golf 5a B-6 list-endpoint fix.
    """

    def test_get_detail_other_tenant_returns_404(
        self, tenant_client: TestClient
    ) -> None:
        """GET /projects/{id} for another tenant's project → 404."""
        project_id = _seed_project("Secret project", "tenant-a")

        resp = tenant_client.get(
            f"/api/v2/projects/{project_id}",
            headers=_auth_headers("bob", "tenant-b"),
        )
        assert resp.status_code == 404

    def test_put_other_tenant_returns_404(
        self, tenant_client: TestClient
    ) -> None:
        """PUT /projects/{id} for another tenant's project → 404 (no mutation)."""
        project_id = _seed_project("Secret project", "tenant-a")

        resp = tenant_client.put(
            f"/api/v2/projects/{project_id}",
            headers=_auth_headers("bob", "tenant-b"),
            data={"name": "Hijacked"},
        )
        assert resp.status_code == 404

        # Confirm the row is unchanged by listing as the owning tenant
        list_resp = tenant_client.get(
            "/api/v2/projects",
            headers=_auth_headers("alice", "tenant-a"),
        )
        names = {p["name"] for p in list_resp.json()["projects"]}
        assert names == {"Secret project"}

    def test_delete_other_tenant_returns_404(
        self, tenant_client: TestClient
    ) -> None:
        """DELETE /projects/{id} for another tenant's project → 404 (no delete)."""
        project_id = _seed_project("Secret project", "tenant-a")

        resp = tenant_client.delete(
            f"/api/v2/projects/{project_id}",
            headers=_auth_headers("bob", "tenant-b"),
        )
        assert resp.status_code == 404

        # Confirm the row is still present for the owning tenant
        list_resp = tenant_client.get(
            "/api/v2/projects",
            headers=_auth_headers("alice", "tenant-a"),
        )
        ids = {p["id"] for p in list_resp.json()["projects"]}
        assert project_id in ids

    def test_files_list_other_tenant_returns_404(
        self, tenant_client: TestClient
    ) -> None:
        """GET /projects/{id}/files for another tenant's project → 404."""
        project_id = _seed_project("Secret project", "tenant-a")
        _seed_project_file(project_id, "ifc", "secret.ifc")

        resp = tenant_client.get(
            f"/api/v2/projects/{project_id}/files",
            headers=_auth_headers("bob", "tenant-b"),
        )
        assert resp.status_code == 404

    def test_file_download_other_tenant_returns_404(
        self, tenant_client: TestClient
    ) -> None:
        """GET /projects/{id}/files/{file_id} for another tenant → 404.

        Even with knowledge of both ids, cross-tenant download must be
        blocked before any disk-path resolution takes place.
        """
        project_id = _seed_project("Secret project", "tenant-a")
        file_id = _seed_project_file(project_id, "ifc", "secret.ifc")

        resp = tenant_client.get(
            f"/api/v2/projects/{project_id}/files/{file_id}",
            headers=_auth_headers("bob", "tenant-b"),
        )
        assert resp.status_code == 404

    def test_file_delete_other_tenant_returns_404(
        self, tenant_client: TestClient
    ) -> None:
        """DELETE /projects/{id}/files/{file_id} for another tenant → 404."""
        project_id = _seed_project("Secret project", "tenant-a")
        file_id = _seed_project_file(project_id, "ifc", "secret.ifc")

        resp = tenant_client.delete(
            f"/api/v2/projects/{project_id}/files/{file_id}",
            headers=_auth_headers("bob", "tenant-b"),
        )
        assert resp.status_code == 404

    def test_legacy_null_tenant_unreachable_by_scoped_caller(
        self, tenant_client: TestClient
    ) -> None:
        """A legacy ``tenant IS NULL`` row must 404 for any tenant-scoped caller.

        Mirrors the list-endpoint fail-closed rule at the detail level:
        even if a tenant-scoped caller learns the id (e.g. from logs or
        an older export), the row stays unreachable until it is
        re-stamped with a tenant slug.
        """
        project_id = _seed_project("Legacy project", None)

        resp = tenant_client.get(
            f"/api/v2/projects/{project_id}",
            headers=_auth_headers("alice", "tenant-a"),
        )
        assert resp.status_code == 404

        # Without an auth header (dev/local), the same id resolves as
        # before — soft-fail branch in ``_get_project_for_tenant``.
        resp_open = tenant_client.get(f"/api/v2/projects/{project_id}")
        # to_dict() lazy-loads files and will hit MissingGreenlet in
        # TestClient (pre-existing, documented), so we can't assert 200
        # here. What matters is that it does NOT 404: the unscoped
        # lookup found the row.
        assert resp_open.status_code != 404


class TestProjectWefcTenantIsolation:
    """.wefc envelope endpoints enforce tenant scoping on the project row.

    The hard ``_resolve_tenant_from_request`` gate already rejects
    unauthenticated calls, but on its own it does not check that the
    URL-path project belongs to the caller's tenant — any authenticated
    tenant user could read or overwrite another tenant's envelope via
    UUID knowledge. The ``_get_project_for_tenant`` call inserted in
    the wefc handlers closes that gap by returning ``404`` on mismatch.
    """

    @staticmethod
    def _mock_registry_for_tenants(slugs: list[str]):
        """Build a mocked registry that returns a config for each slug."""

        def _get(slug: str) -> MagicMock | None:
            if slug not in slugs:
                return None
            config = MagicMock()
            config.slug = slug
            config.has_volume_mount = False
            return config

        registry = MagicMock()
        registry.is_configured = True
        registry.get.side_effect = _get
        return registry

    def test_wefc_get_other_tenant_returns_404(
        self, tenant_client: TestClient
    ) -> None:
        """GET /projects/{id}/wefc for another tenant's project → 404."""
        project_id = _seed_project("Secret project", "tenant-a")

        registry = self._mock_registry_for_tenants(["tenant-a", "tenant-b"])
        with patch(
            "server.routers.projects.get_tenants",
            return_value=registry,
        ):
            resp = tenant_client.get(
                f"/api/v2/projects/{project_id}/wefc",
                headers=_auth_headers("bob", "tenant-b"),
            )
        assert resp.status_code == 404

    def test_wefc_put_other_tenant_returns_404(
        self, tenant_client: TestClient
    ) -> None:
        """PUT /projects/{id}/wefc for another tenant's project → 404 (no write)."""
        project_id = _seed_project("Secret project", "tenant-a")

        registry = self._mock_registry_for_tenants(["tenant-a", "tenant-b"])
        with patch(
            "server.routers.projects.get_tenants",
            return_value=registry,
        ):
            resp = tenant_client.put(
                f"/api/v2/projects/{project_id}/wefc",
                headers=_auth_headers("bob", "tenant-b"),
                json={"header": {"schema": "WeFC"}},
            )
        assert resp.status_code == 404
