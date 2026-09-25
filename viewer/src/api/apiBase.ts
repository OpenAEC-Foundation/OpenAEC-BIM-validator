/**
 * Tauri detection + API origin resolution.
 *
 * On the web the React app is served by the FastAPI server itself, so a
 * relative base ("/api/...") is correct. In the Tauri desktop app the UI is
 * served from tauri://localhost (http://tauri.localhost on Windows), so calls
 * must target the embedded server explicitly at 127.0.0.1:8000.
 */
function detectTauri(): boolean {
  return (
    typeof window !== "undefined" &&
    ("__TAURI_INTERNALS__" in window || "__TAURI__" in window)
  );
}

/** True when running inside the Tauri desktop shell. */
export const IS_TAURI = detectTauri();

function resolveApiOrigin(): string {
  const env = import.meta.env as unknown as Record<string, string | undefined>;
  const override = env.VITE_API_ORIGIN;
  if (override) return override.replace(/\/+$/, "");
  return IS_TAURI ? "http://127.0.0.1:8000" : "";
}

/** API origin: "" on the web (relative), absolute server URL inside Tauri. */
export const API_ORIGIN = resolveApiOrigin();
