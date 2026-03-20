/// <reference types="vite/client" />

export interface OidcConfig {
  enabled: boolean;
  authority: string;
  clientId: string;
  redirectUri: string;
  scopes: string;
  authorizationEndpoint: string;
}

let _cachedConfig: OidcConfig | null = null;

export async function getOidcConfig(): Promise<OidcConfig> {
  if (_cachedConfig) return _cachedConfig;

  try {
    const res = await fetch("/api/auth/oidc/config");
    if (res.ok) {
      _cachedConfig = await res.json();
      return _cachedConfig!;
    }
  } catch {
    // Server not available
  }

  // Fallback: try well-known Authentik discovery
  const authority = import.meta.env.VITE_OIDC_AUTHORITY || "https://auth.open-aec.com";
  try {
    const wellKnown = await fetch(
      `${authority}/application/o/openaec-bim-validator/.well-known/openid-configuration`
    );
    if (wellKnown.ok) {
      const disc = await wellKnown.json();
      _cachedConfig = {
        enabled: true,
        authority,
        clientId: import.meta.env.VITE_OIDC_CLIENT_ID ?? "openaec-bim-validator",
        redirectUri: import.meta.env.VITE_OIDC_REDIRECT_URI ?? window.location.origin,
        scopes: "openid profile email openaec_profile",
        authorizationEndpoint: disc.authorization_endpoint ?? "",
      };
      return _cachedConfig;
    }
  } catch {
    // Authentik not reachable
  }

  // Final fallback: env vars
  _cachedConfig = {
    enabled: import.meta.env.VITE_OIDC_ENABLED === "true",
    authority,
    clientId: import.meta.env.VITE_OIDC_CLIENT_ID ?? "openaec-bim-validator",
    redirectUri: import.meta.env.VITE_OIDC_REDIRECT_URI ?? window.location.origin,
    scopes: "openid profile email openaec_profile",
    authorizationEndpoint: "",
  };
  return _cachedConfig;
}

export function isOidcPossiblyEnabled(): boolean {
  if (_cachedConfig) return _cachedConfig.enabled;
  return import.meta.env.VITE_OIDC_ENABLED === "true";
}
