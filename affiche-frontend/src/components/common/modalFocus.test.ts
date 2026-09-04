import { describe, expect, it } from 'vitest';

import { wrapFocusIndex } from './modalFocus';

describe('wrapFocusIndex', () => {
  it('leaves the middle of the list to the browser', () => {
    expect(wrapFocusIndex(4, 1, false)).toBe(-1);
    expect(wrapFocusIndex(4, 2, true)).toBe(-1);
  });

  it('wraps forward off the end', () => {
    expect(wrapFocusIndex(4, 3, false)).toBe(0);
  });

  it('wraps backward off the start', () => {
    expect(wrapFocusIndex(4, 0, true)).toBe(3);
  });

  it('does not wrap forward off the start, nor backward off the end', () => {
    expect(wrapFocusIndex(4, 0, false)).toBe(-1);
    expect(wrapFocusIndex(4, 3, true)).toBe(-1);
  });

  it('enters the list when focus is on the panel', () => {
    expect(wrapFocusIndex(4, -1, false)).toBe(0);
    expect(wrapFocusIndex(4, -1, true)).toBe(3);
  });

  it('has nothing to focus in an empty dialog', () => {
    expect(wrapFocusIndex(0, -1, false)).toBe(-1);
    expect(wrapFocusIndex(0, -1, true)).toBe(-1);
  });

  it('keeps a lone control focused', () => {
    expect(wrapFocusIndex(1, 0, false)).toBe(0);
    expect(wrapFocusIndex(1, 0, true)).toBe(0);
  });
});
