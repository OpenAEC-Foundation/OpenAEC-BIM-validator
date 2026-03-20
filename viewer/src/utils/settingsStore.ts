const PREFIX = "openaec-bim-validator:";

export function getSetting(key: string, fallback: string): string {
  try {
    return localStorage.getItem(PREFIX + key) ?? fallback;
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

export function applyTheme(theme?: string): void {
  document.documentElement.setAttribute("data-theme", theme || "light");
}
