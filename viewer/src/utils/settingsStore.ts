import { applyDisplay, type Theme } from "@openaec/ui-react";
const PREFIX = "openaec-bim-validator:";

export function getSetting(key: string, fallback: string): string {
  try {
    const value = localStorage.getItem(PREFIX + key) ?? fallback;
    return key === "theme" ? normalizeTheme(value) : value;
  } catch {
    return fallback;
  }
}

export function setSetting(key: string, value: string): void {
  try {
    localStorage.setItem(PREFIX + key, value);
  } catch {
    // localStorage unavailable
  }
}

export function normalizeTheme(theme?: string): Theme {
  const legacy: Record<string, Theme> = { forge: "dark", openaec: "dark", contrast: "high-contrast-dark" };
  const themes: Theme[] = ["light", "dark", "blueprint", "high-contrast-dark", "high-contrast-light"];
  const normalized = legacy[theme ?? ""] ?? (themes.includes(theme as Theme) ? theme as Theme : "light");
  return normalized;
}

export function applyTheme(theme?: string): void {
  document.documentElement.removeAttribute("data-theme");
  applyDisplay({ theme: normalizeTheme(theme) });
}
