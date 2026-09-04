import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  THEME_STORAGE_KEY,
  applyTheme,
  isThemePreference,
  readStoredTheme,
  resolveTheme,
  storeTheme,
} from './theme';

afterEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
});

const stubMatchMedia = (matches: boolean) => {
  vi.stubGlobal('matchMedia', () => ({
    matches,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
};

describe('resolveTheme', () => {
  it('follows the system preference when set to system', () => {
    expect(resolveTheme('system', true)).toBe('dark');
    expect(resolveTheme('system', false)).toBe('light');
  });

  it('ignores the system preference when set explicitly', () => {
    expect(resolveTheme('light', true)).toBe('light');
    expect(resolveTheme('dark', false)).toBe('dark');
  });

  it('never returns system, which matches no palette', () => {
    for (const systemDark of [true, false]) {
      expect(['light', 'dark']).toContain(resolveTheme('system', systemDark));
    }
  });
});

describe('readStoredTheme', () => {
  it('defaults to system when nothing is stored', () => {
    expect(readStoredTheme()).toBe('system');
  });

  it('reads back what was stored', () => {
    storeTheme('light');
    expect(readStoredTheme()).toBe('light');
  });

  it('falls back to system for a value it does not recognise', () => {

    localStorage.setItem(THEME_STORAGE_KEY, 'sepia');
    expect(readStoredTheme()).toBe('system');
  });
});

describe('isThemePreference', () => {
  it('accepts the three preferences and rejects anything else', () => {
    expect(isThemePreference('system')).toBe(true);
    expect(isThemePreference('light')).toBe(true);
    expect(isThemePreference('dark')).toBe(true);
    expect(isThemePreference('sepia')).toBe(false);
    expect(isThemePreference(null)).toBe(false);
  });
});

describe('applyTheme', () => {
  it('writes a concrete theme onto the document element', () => {
    stubMatchMedia(false);

    expect(applyTheme('system')).toBe('light');
    expect(document.documentElement.dataset.theme).toBe('light');
  });

  it('writes the explicit choice regardless of the system preference', () => {
    stubMatchMedia(true);

    expect(applyTheme('light')).toBe('light');
    expect(document.documentElement.dataset.theme).toBe('light');
  });
});
