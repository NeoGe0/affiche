import { describe, expect, it } from 'vitest';

import { DEFAULT_VIEW_MODE, parseViewMode } from './viewMode';

describe('parseViewMode', () => {
  it('accepts the two real modes', () => {
    expect(parseViewMode('grid')).toBe('grid');
    expect(parseViewMode('list')).toBe('list');
  });

  it('falls back to the default when nothing is stored', () => {
    expect(parseViewMode(null)).toBe(DEFAULT_VIEW_MODE);
    expect(parseViewMode('')).toBe(DEFAULT_VIEW_MODE);
  });

  it('falls back to the default for an unrecognised value', () => {
    expect(parseViewMode('table')).toBe(DEFAULT_VIEW_MODE);
    expect(parseViewMode('Grid')).toBe(DEFAULT_VIEW_MODE);
    expect(parseViewMode('{"mode":"list"}')).toBe(DEFAULT_VIEW_MODE);
  });
});
