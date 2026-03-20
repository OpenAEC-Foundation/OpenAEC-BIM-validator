/**
 * App Component
 *
 * Entry point that renders either the new 3-panel BIM platform layout
 * (AppShell) or the legacy validation-only view, depending on URL path.
 *
 * - "/" or "/viewer" → AppShell (3-panel BIM platform)
 * - "/validate" → Legacy validation flow (original single-page app)
 */

import { useEffect } from "react";

import { AppShell } from "./components/layout/AppShell";
import { LegacyValidationView } from "./LegacyValidationView";
import { getSetting, applyTheme } from "./utils/settingsStore";

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

  if (isLegacyView) {
    return <LegacyValidationView />;
  }

  return <AppShell />;
}

export default App;
