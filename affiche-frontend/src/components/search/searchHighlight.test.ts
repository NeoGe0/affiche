import { describe, expect, it } from 'vitest';

import { moveHighlight } from './searchHighlight';

describe('moveHighlight', () => {
  it('walks down and up the list', () => {
    expect(moveHighlight(3, 0, 'ArrowDown')).toBe(1);
    expect(moveHighlight(3, 2, 'ArrowUp')).toBe(1);
  });

  it('wraps at both ends, so a held key cycles rather than sticking', () => {
    expect(moveHighlight(3, 2, 'ArrowDown')).toBe(0);
    expect(moveHighlight(3, 0, 'ArrowUp')).toBe(2);
  });

  it('jumps to either end', () => {
    expect(moveHighlight(4, 2, 'Home')).toBe(0);
    expect(moveHighlight(4, 1, 'End')).toBe(3);
  });

  it('leaves a key it does not own alone', () => {
    expect(moveHighlight(3, 0, 'ArrowLeft')).toBeNull();
    expect(moveHighlight(3, 0, 'a')).toBeNull();
  });

  it('has nothing to move in an empty list', () => {

    expect(moveHighlight(0, 0, 'ArrowDown')).toBeNull();
  });
});
