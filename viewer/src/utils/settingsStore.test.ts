import { describe, it, expect } from 'vitest';
import { applyTheme } from './settingsStore';

describe('Blueprint display migration', () => {
  it.each([['forge', 'dark'], ['openaec', 'dark'], ['contrast', 'high-contrast-dark'], ['blueprint', 'blueprint'], ['high-contrast-light', 'high-contrast-light']])('migrates %s to %s', (old, expected) => {
    document.documentElement.setAttribute('data-theme', old);
    applyTheme(old);
    expect(document.documentElement.getAttribute('data-oa-theme')).toBe(expected);
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
  });
  it('falls back to the upstream light default for an unknown preference', () => {
    applyTheme('unknown');
    expect(document.documentElement.hasAttribute('data-oa-theme')).toBe(false);
  });
});
