"""
Multi-tenant configuration loader.

Loads tenant definitions from tenants.json and resolves
service account passwords from environment variables.

Each tenant maps to a Nextcloud instance with:
- WebDAV URL for writes
- Volume mount path for direct reads
- Service account credentials
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

TENANTS_CONFIG_PATH = os.environ.get(
    "TENANTS_CONFIG", "/etc/openaec/tenants.json"
)


@dataclass(frozen=True)
class TenantConfig:
    """Configuration for a single tenant."""

    slug: str
    name: str
    nextcloud_url: str
    nextcloud_domain: str
    service_user: str
    service_pass: str
    group_folder_id: int = 1
    volume_mount: str = ""  # resolved at load time

    @property
    def volume_path(self) -> Path:
        """Absolute path to the NC data volume mount."""
        return Path(self.volume_mount)

    @property
    def projects_root(self) -> Path:
        """Path to the group folder files root."""
        return self.volume_path / f"__groupfolders/{self.group_folder_id}/files"

    @property
    def has_volume_mount(self) -> bool:
        """Check if the volume mount is available on disk."""
        return self.volume_mount != "" and self.projects_root.is_dir()


@dataclass
class TenantsRegistry:
    """Registry of all configured tenants."""

    tenants: dict[str, TenantConfig] = field(default_factory=dict)

    def get(self, slug: str) -> TenantConfig | None:
        """Get tenant config by slug."""
        return self.tenants.get(slug)

    def get_or_raise(self, slug: str) -> TenantConfig:
        """Get tenant config by slug, raise if not found."""
        tenant = self.tenants.get(slug)
        if not tenant:
            raise ValueError(f"Unknown tenant: {slug}")
        return tenant

    @property
    def slugs(self) -> list[str]:
        """List all tenant slugs."""
        return list(self.tenants.keys())

    @property
    def is_configured(self) -> bool:
        """Check if any tenants are configured."""
        return len(self.tenants) > 0


def load_tenants(config_path: str | None = None) -> TenantsRegistry:
    """Load tenant configuration from JSON file.

    Args:
        config_path: Path to tenants.json. Defaults to TENANTS_CONFIG env var.

    Returns:
        TenantsRegistry with all configured tenants.
    """
    path = config_path or TENANTS_CONFIG_PATH
    registry = TenantsRegistry()

    if not Path(path).is_file():
        logger.info("No tenants config at %s — multi-tenant disabled", path)
        return registry

    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load tenants config: %s", exc)
        return registry

    for slug, tenant_data in data.get("tenants", {}).items():
        # Resolve password from environment
        pass_env = tenant_data.get("service_pass_env", "")
        service_pass = os.environ.get(pass_env, "")
        if not service_pass:
            logger.warning(
                "Tenant %s: password env var %s not set — skipping",
                slug, pass_env,
            )
            continue

        # Volume mount path: /nc-data-{slug}
        volume_mount = f"/nc-data-{slug}"

        tenant = TenantConfig(
            slug=slug,
            name=tenant_data.get("name", slug),
            nextcloud_url=tenant_data.get("nextcloud_url", ""),
            nextcloud_domain=tenant_data.get("nextcloud_domain", ""),
            service_user=tenant_data.get("service_user", "openaec-service"),
            service_pass=service_pass,
            group_folder_id=tenant_data.get("group_folder_id", 1),
            volume_mount=volume_mount,
        )
        registry.tenants[slug] = tenant
        logger.info(
            "Loaded tenant %s: NC=%s, volume=%s (mounted=%s)",
            slug,
            tenant.nextcloud_url,
            volume_mount,
            tenant.has_volume_mount,
        )

    return registry


# ── Singleton ──────────────────────────────────────────────────

_registry: TenantsRegistry | None = None


def get_tenants() -> TenantsRegistry:
    """Get the global tenants registry (lazy-loaded singleton)."""
    global _registry
    if _registry is None:
        _registry = load_tenants()
    return _registry


def get_tenant(slug: str) -> TenantConfig:
    """Get a specific tenant config, raising if not found."""
    return get_tenants().get_or_raise(slug)
