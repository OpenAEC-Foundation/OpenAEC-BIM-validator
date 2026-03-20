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

  // Fallback to environment variables
  _cachedConfig = {
    enabled: import.meta.env.VITE_OIDC_ENABLED === "true",
    authority: import.meta.env.VITE_OIDC_AUTHORITY ?? "",
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
