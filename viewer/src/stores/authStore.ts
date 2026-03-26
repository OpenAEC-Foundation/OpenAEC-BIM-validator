import { create } from "zustand";
import {
  isOidcConfigured,
  initOidc,
  signinRedirect,
  processOidcCallback,
  getSignedInUser,
  signout,
} from "../lib/oidcManager";

export interface AuthUser {
  username: string;
  display_name: string;
  email: string;
}

interface AuthState {
  user: AuthUser | null;
  oidcEnabled: boolean;
  loading: boolean;
  checkAuth: () => Promise<void>;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

let oidcInitialized = false;

function ensureOidcInit() {
  if (!oidcInitialized && isOidcConfigured()) {
    initOidc();
    oidcInitialized = true;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  oidcEnabled: isOidcConfigured(),
  loading: false,

  checkAuth: async () => {
    if (!isOidcConfigured()) return;

    set({ loading: true });
    try {
      ensureOidcInit();

      // Check for OIDC callback (code in URL after redirect from Authentik)
      const callbackUser = await processOidcCallback();
      if (callbackUser) {
        set({
          user: {
            username: callbackUser.name,
            display_name: callbackUser.name,
            email: callbackUser.email,
          },
          loading: false,
        });
        return;
      }

      // Check for existing session
      const existing = await getSignedInUser();
      if (existing) {
        set({
          user: {
            username: existing.name,
            display_name: existing.name,
            email: existing.email,
          },
          loading: false,
        });
        return;
      }

      set({ user: null, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },

  login: async () => {
    try {
      ensureOidcInit();
      await signinRedirect();
      // Browser redirects away — no code after this runs
    } catch (err) {
      console.error("OIDC login failed:", err);
    }
  },

  logout: async () => {
    try {
      await signout();
    } catch {
      // signout may fail if not initialized
    }
    set({ user: null });
  },
}));
