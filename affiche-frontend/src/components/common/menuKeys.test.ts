import { describe, expect, it } from 'vitest';

import { menuFocusIndex } from './menuKeys';

describe('menuFocusIndex', () => {
  const all = [true, true, true];

  it('moves down and up, wrapping at the ends', () => {
    expect(menuFocusIndex('ArrowDown', 0, all)).toBe(1);
    expect(menuFocusIndex('ArrowDown', 2, all)).toBe(0);
    expect(menuFocusIndex('ArrowUp', 0, all)).toBe(2);
  });

  it('jumps to the first and last items', () => {
    expect(menuFocusIndex('Home', 2, all)).toBe(0);
    expect(menuFocusIndex('End', 0, all)).toBe(2);
  });

  it('skips disabled items', () => {
    expect(menuFocusIndex('ArrowDown', 0, [true, false, true])).toBe(2);
    expect(menuFocusIndex('Home', 2, [false, true, true])).toBe(1);
  });

  it('ignores keys it does not handle, and menus with nothing to focus', () => {
    expect(menuFocusIndex('a', 0, all)).toBeNull();
    expect(menuFocusIndex('ArrowDown', 0, [false, false])).toBeNull();
  });
});
