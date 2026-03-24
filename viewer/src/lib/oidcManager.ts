/**
 * OIDC manager — thin wrapper around oidc-client-ts for Authentik SSO.
 *
 * Handles:
 * - Redirect-based login flow
 * - Callback processing on page load
 * - Silent token renewal
 * - Logout
 *
 * Config via Vite env vars:
 *   VITE_OIDC_AUTHORITY  — Authentik issuer URL
 *   VITE_OIDC_CLIENT_ID  — OIDC client ID
 */

import { UserManager, type User, WebStorageStateStore } from "oidc-client-ts";

let userManager: UserManager | null = null;

export interface OidcUser {
  name: string;
  email: string;
  sub: string;
  accessToken: string;
  expiresAt: number;
}

/**
 * Initialize the OIDC UserManager with Authentik config.
 * Call once on app startup.
 */
export function initOidc(): UserManager {
  const authority = import.meta.env.VITE_OIDC_AUTHORITY as string | undefined;
  const clientId = import.meta.env.VITE_OIDC_CLIENT_ID as string | undefined;

  if (!authority || !clientId) {
    throw new Error(
      "OIDC not configured: set VITE_OIDC_AUTHORITY and VITE_OIDC_CLIENT_ID",
    );
  }

  userManager = new UserManager({
    authority,
    client_id: clientId,
    redirect_uri: `${window.location.origin}/oidc-callback`,
    post_logout_redirect_uri: window.location.origin,
    response_type: "code",
    scope: "openid profile email",
    automaticSilentRenew: true,
    userStore: new WebStorageStateStore({ store: sessionStorage }),
  });

  return userManager;
}

/**
 * Get the existing UserManager (must call initOidc first).
 */
export function getOidcManager(): UserManager {
  if (!userManager) {
    throw new Error("OIDC not initialized — call initOidc() first");
  }
  return userManager;
}

/**
 * Check if OIDC is configured (env vars present).
 */
export function isOidcConfigured(): boolean {
  return !!(
    import.meta.env.VITE_OIDC_AUTHORITY &&
    import.meta.env.VITE_OIDC_CLIENT_ID
  );
}

/**
 * Start the OIDC login redirect.
 */
export async function signinRedirect(): Promise<void> {
  const mgr = getOidcManager();
  await mgr.signinRedirect();
}

/**
 * Process the OIDC callback after redirect back from Authentik.
 * Call this when the URL contains a `code` parameter.
 * Returns the authenticated user or null if not a callback URL.
 */
export async function processOidcCallback(): Promise<OidcUser | null> {
  const params = new URLSearchParams(window.location.search);
  if (!params.has("code")) return null;

  try {
    const mgr = getOidcManager();
    const user = await mgr.signinRedirectCallback();

    // Clean the URL
    window.history.replaceState({}, document.title, window.location.pathname);

    return mapUser(user);
  } catch (err) {
    console.error("OIDC callback error:", err);
    // Clean URL even on error
    window.history.replaceState({}, document.title, window.location.pathname);
    return null;
  }
}

/**
 * Get the current signed-in user (from session storage).
 */
export async function getSignedInUser(): Promise<OidcUser | null> {
  try {
    const mgr = getOidcManager();
    const user = await mgr.getUser();
    if (!user || user.expired) return null;
    return mapUser(user);
  } catch {
    return null;
  }
}

/**
 * Sign out: remove local session and redirect to Authentik logout.
 */
export async function signout(): Promise<void> {
  try {
    const mgr = getOidcManager();
    await mgr.signoutRedirect();
  } catch {
    // If signout redirect fails, at least clear local state
    const mgr = getOidcManager();
    await mgr.removeUser();
  }
}

/**
 * Register a callback for when the token is silently renewed.
 */
export function onTokenRenewed(
  callback: (user: OidcUser) => void,
): () => void {
  const mgr = getOidcManager();
  const handler = (user: User | null) => {
    if (user) callback(mapUser(user));
  };
  mgr.events.addUserLoaded(handler);
  return () => mgr.events.removeUserLoaded(handler);
}

// ── Internal ───────────────────────────────────────────────

function mapUser(user: User): OidcUser {
  return {
    name: (user.profile.name ?? user.profile.preferred_username ?? "Unknown") as string,
    email: (user.profile.email ?? "") as string,
    sub: user.profile.sub,
    accessToken: user.access_token,
    expiresAt: (user.expires_at ?? 0) * 1000, // convert to epoch ms
  };
}
