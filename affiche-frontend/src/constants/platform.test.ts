import { afterEach, describe, expect, it, vi } from 'vitest';

import { searchShortcutLabel } from './platform';

afterEach(() => vi.unstubAllGlobals());

const onPlatform = (platform: string) => vi.stubGlobal('navigator', { platform });

describe('searchShortcutLabel', () => {
  it('writes the shortcut the way the platform does', () => {
    onPlatform('MacIntel');
    expect(searchShortcutLabel()).toBe('⌘K');

    onPlatform('Win32');
    expect(searchShortcutLabel()).toBe('Ctrl K');
  });

  it('prefers the client-hints platform where the browser offers it', () => {
    vi.stubGlobal('navigator', { platform: 'Win32', userAgentData: { platform: 'macOS' } });
    expect(searchShortcutLabel()).toBe('⌘K');
  });
});
