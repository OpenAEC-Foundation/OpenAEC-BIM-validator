/**
 * Build-time feature flags. Configured per environment via `.env.*` files
 * (Vite). One source of truth — not scattered across loose imports.
 */

const env = import.meta.env as unknown as Record<string, string | undefined>;

/**
 * Whether the OpenAEC integrations (login + cloud storage) are visible and
 * reachable. Off by default (public builds show no platform coupling); set
 * `VITE_OPENAEC_ENABLED=true` in `.env.development` or `.env.production` to
 * enable it in your own build.
 */
export const OPENAEC_ENABLED = env.VITE_OPENAEC_ENABLED === "true";
