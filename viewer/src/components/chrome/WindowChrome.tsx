import { IconButton, Button as OaButton } from "@openaec/ui-react";
/**
 * WindowChrome — slim OS-level title bar for the Tauri desktop app.
 *
 * The app runs with `decorations: false`, so this thin strip provides the
 * draggable region and minimize/maximize/close controls. It sits ABOVE the
 * app's own in-app header and is mounted only inside Tauri (see App.tsx), so
 * the web build is completely unaffected. Uses its own `.window-chrome*`
 * classes to avoid colliding with the existing `.titlebar` app header.
 *
 * When OPENAEC_ENABLED, an OpenAEC "Sign in" button (logged out) or an
 * avatar + dropdown with sign-out (logged in) is shown on the right, before
 * the window controls. The OIDC/PKCE flow lives entirely in Rust.
 */
import { useEffect, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";

import { useStore } from "../../store";
import { OPENAEC_ENABLED } from "../../services/buildFlags";

import "./WindowChrome.css";

export function WindowChrome() {
  const win = getCurrentWindow();

  // OpenAEC account (login via Rust/OIDC; tokens stay in the keyring)
  const accountsUser = useStore((s) => s.accountsUser);
  const accountsBusy = useStore((s) => s.accountsBusy);
  const accountsSignIn = useStore((s) => s.accountsSignIn);
  const accountsSignOut = useStore((s) => s.accountsSignOut);
  const accountsLoadUser = useStore((s) => s.accountsLoadUser);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);

  // Restore session from the keyring on mount.
  useEffect(() => {
    if (OPENAEC_ENABLED) void accountsLoadUser();
  }, [accountsLoadUser]);

  // Close the dropdown on any outside click.
  useEffect(() => {
    if (!accountMenuOpen) return;
    const close = () => setAccountMenuOpen(false);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, [accountMenuOpen]);

  const accountInitials = accountsUser
    ? (accountsUser.name || accountsUser.email)
        .split(/[\s@.]+/)
        .filter(Boolean)
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "";

  const handleSignIn = async () => {
    try {
      await accountsSignIn();
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert(`Inloggen mislukt: ${e}`);
    }
  };

  return (
    <div className="window-chrome">
      <div className="window-chrome__drag" data-tauri-drag-region>
        <span className="window-chrome__mark" aria-hidden="true" />
        <span className="window-chrome__title">BIM Validator</span>
      </div>
      <div className="window-chrome__controls">
        {OPENAEC_ENABLED && accountsUser ? (
          <div className="window-chrome__account" onClick={(e) => e.stopPropagation()}>
            <OaButton
              type="button"
              className="window-chrome__account-btn"
              onClick={() => setAccountMenuOpen((v) => !v)}
              title={accountsUser.email}
            >
              <span className="window-chrome__avatar">{accountInitials}</span>
              <span className="window-chrome__account-name">
                {accountsUser.name || accountsUser.email}
              </span>
            </OaButton>
            {accountMenuOpen && (
              <div className="window-chrome__account-menu">
                <div className="window-chrome__account-menu-header">
                  <div className="window-chrome__account-menu-name">{accountsUser.name}</div>
                  <div className="window-chrome__account-menu-email">{accountsUser.email}</div>
                </div>
                <OaButton kind="quiet"
                  type="button"
                  className="window-chrome__account-menu-item"
                  onClick={() => {
                    setAccountMenuOpen(false);
                    void accountsSignOut();
                  }}
                >
                  Uitloggen
                </OaButton>
              </div>
            )}
          </div>
        ) : OPENAEC_ENABLED ? (
          <OaButton
            type="button"
            className="window-chrome__signin-btn"
            onClick={handleSignIn}
            disabled={accountsBusy}
          >
            {accountsBusy ? "Bezig met inloggen…" : "Inloggen met OpenAEC"}
          </OaButton>
        ) : null}
        <IconButton className="window-chrome__btn" icon="window.minimize" label="Minimaliseren" onClick={() => void win.minimize()} />
        <IconButton className="window-chrome__btn" icon="window.maximize" label="Maximaliseren" onClick={() => void win.toggleMaximize()} />
        <IconButton className="window-chrome__btn" icon="window.close" label="Sluiten" onClick={() => void win.close()} />
      </div>
    </div>
  );
}
