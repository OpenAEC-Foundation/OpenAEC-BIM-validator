/**
 * OpenAEC Accounts slice — login state for "Sign in with OpenAEC".
 *
 * The OAuth/PKCE flow and tokens live entirely on the Rust side (keyring);
 * this slice only talks via Tauri commands and never holds any secrets.
 * Ported from the working open-calc-studio implementation.
 */

import type { StateCreator } from "zustand";

export interface AccountsUser {
  sub: string;
  name: string;
  email: string;
}

export interface AccountsSlice {
  accountsUser: AccountsUser | null;
  accountsBusy: boolean;
  accountsError: string | null;
  /** Start the browser login flow; sets accountsUser on success. */
  accountsSignIn: () => Promise<void>;
  accountsSignOut: () => Promise<void>;
  /** Restore the session from the keyring (on app start). */
  accountsLoadUser: () => Promise<void>;
}

async function tauriInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(cmd, args);
}

export const createAccountsSlice: StateCreator<AccountsSlice> = (set, get) => ({
  accountsUser: null,
  accountsBusy: false,
  accountsError: null,

  accountsSignIn: async () => {
    // One login at a time: the loopback port can only have one listener.
    if (get().accountsBusy) return;
    set({ accountsBusy: true, accountsError: null });
    try {
      const user = await tauriInvoke<AccountsUser>("accounts_sign_in");
      set({ accountsUser: user, accountsBusy: false });
      // Register this app in "My apps" on the account (idempotent; 409 = already
      // added) — fire-and-forget.
      tauriInvoke("accounts_fetch", {
        path: "/me/apps",
        method: "POST",
        body: { slug: "openaec-bim-validator" },
      }).catch(() => {});
    } catch (e) {
      set({ accountsBusy: false, accountsError: String(e) });
      throw e;
    }
  },

  accountsSignOut: async () => {
    try {
      await tauriInvoke("accounts_sign_out");
    } catch {
      // browser mode or command unavailable — local sign-out is enough
    }
    set({ accountsUser: null });
  },

  accountsLoadUser: async () => {
    try {
      const user = await tauriInvoke<AccountsUser | null>("accounts_get_user");
      if (user) set({ accountsUser: user });
    } catch {
      // no Tauri (browser mode) — silently skip
    }
  },
});
