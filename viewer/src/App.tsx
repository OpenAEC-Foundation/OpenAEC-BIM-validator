/**
 * App Component
 *
 * Entry point that renders either the new 3-panel BIM platform layout
 * (AppShell) or the legacy validation-only view, depending on URL path.
 *
 * - "/" or "/viewer" → AppShell (3-panel BIM platform)
 * - "/validate" → Legacy validation flow (original single-page app)
 *
 * Inside the Tauri desktop app (decorations: false) the whole view is wrapped
 * in a flex shell with a slim OS title bar (WindowChrome) on top. On the web
 * this wrapper is skipped entirely.
 */

import { useEffect } from "react";

import { AppShell } from "./components/layout/AppShell";
import { LegacyValidationView } from "./LegacyValidationView";
import { getSetting, applyTheme } from "./utils/settingsStore";
import { IS_TAURI } from "./api/apiBase";
import { WindowChrome } from "./components/chrome/WindowChrome";

// Styles
import "./App.css";

/**
 * Main App component — routes between platform and legacy views.
 */
export function App() {
  // Apply persisted theme on mount
  useEffect(() => {
    applyTheme(getSetting("theme", "light"));
  }, []);

  // Simple path-based routing (no router dependency needed)
  const path = window.location.pathname;
  const isLegacyView = path.startsWith("/validate");
  const content = isLegacyView ? <LegacyValidationView /> : <AppShell />;

  // Tauri desktop: add the custom OS title bar above the app.
  if (IS_TAURI) {
    return (
      <div className="tauri-shell">
        <WindowChrome />
        <div className="tauri-shell__content">{content}</div>
      </div>
    );
  }

  return content;
}

export default App;
