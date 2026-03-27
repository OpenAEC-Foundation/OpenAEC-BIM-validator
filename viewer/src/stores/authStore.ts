import { create } from "zustand";

export interface AuthUser {
  username: string;
  display_name: string;
  email: string;
}

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  checkAuth: () => Promise<void>;
  login: () => void;
  logout: () => void;
}

/**
 * Auth store — reads user identity from the Authentik proxy.
 *
 * The site sits behind an Authentik Forward Auth outpost that sets
 * X-authentik-* headers on every request.  The backend exposes these
 * via GET /api/auth/me so the frontend can pick them up.
 *
 * If the proxy is not present (e.g. local dev without auth) the
 * endpoint returns 401 and the user stays anonymous.
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,

  checkAuth: async () => {
    set({ loading: true });
    try {
      const res = await fetch("/api/auth/me");
      if (res.ok) {
        const data: AuthUser = await res.json();
        set({ user: data, loading: false });
        return;
      }
      set({ user: null, loading: false });
    } catch {
      // Network error or backend unavailable
      set({ user: null, loading: false });
    }
  },

  login: () => {
    // The proxy handles authentication.  Reloading the page triggers
    // the Authentik login redirect if the session has expired.
    window.location.reload();
  },

  logout: () => {
    // Redirect to the Authentik end-session endpoint.
    // After logout Authentik redirects back to the app, where the
    // proxy will show the login screen again.
    set({ user: null });
    window.location.href =
      "https://auth.open-aec.com/application/o/bim-validator-oidc/end-session/";
  },
}));
