import { create } from "zustand";

export interface AuthUser {
  username: string;
  display_name: string;
  role: string;
  tenant?: string;
}

interface AuthState {
  user: AuthUser | null;
  oidcEnabled: boolean;
  loading: boolean;
  checkAuth: () => Promise<void>;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  oidcEnabled: false,
  loading: false,

  checkAuth: async () => {
    set({ loading: true });
    try {
      const res = await fetch("/api/auth/me", { credentials: "include" });
      if (res.ok) {
        const user: AuthUser = await res.json();
        set({ user, loading: false });
      } else {
        set({ user: null, loading: false });
      }
    } catch {
      set({ user: null, loading: false });
    }

    // Check OIDC availability
    try {
      const { getOidcConfig } = await import("../config/oidc");
      const config = await getOidcConfig();
      set({ oidcEnabled: config.enabled });
    } catch {
      set({ oidcEnabled: false });
    }
  },

  login: async () => {
    try {
      const { getOidcConfig } = await import("../config/oidc");
      const config = await getOidcConfig();
      if (!config.enabled || !config.authorizationEndpoint) return;

      // PKCE code verifier
      const codeVerifier = crypto.getRandomValues(new Uint8Array(32));
      const encoded = btoa(String.fromCharCode(...codeVerifier))
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/, "");
      sessionStorage.setItem("oidc_code_verifier", encoded);

      const hashBuffer = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(encoded)
      );
      const codeChallenge = btoa(String.fromCharCode(...new Uint8Array(hashBuffer)))
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/, "");

      const params = new URLSearchParams({
        response_type: "code",
        client_id: config.clientId,
        redirect_uri: config.redirectUri,
        scope: config.scopes,
        code_challenge: codeChallenge,
        code_challenge_method: "S256",
      });

      window.location.href = `${config.authorizationEndpoint}?${params}`;
    } catch {
      // OIDC not available
    }
  },

  logout: async () => {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Server not available
    }
    set({ user: null });
    const { loading: _l, ...state } = get();
    void _l;
    void state;
  },
}));
