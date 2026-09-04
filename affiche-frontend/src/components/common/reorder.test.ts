import { describe, expect, it } from 'vitest';

import { moveItem } from './reorder';

describe('moveItem', () => {
  it('moves an entry up', () => {
    expect(moveItem(['a', 'b', 'c'], 2, 0)).toEqual(['c', 'a', 'b']);
  });

  it('moves an entry down', () => {
    expect(moveItem(['a', 'b', 'c'], 0, 1)).toEqual(['b', 'a', 'c']);
  });

  it('leaves the input untouched', () => {
    const order = ['a', 'b', 'c'];

    moveItem(order, 0, 2);

    expect(order).toEqual(['a', 'b', 'c']);
  });

  it('returns the very same array when the entry does not move', () => {
    const order = ['a', 'b', 'c'];

    expect(moveItem(order, 1, 1)).toBe(order);
  });

  it.each([
    ['past the end', 2, 3],
    ['before the start', 0, -1],
    ['from outside the list', 5, 0],
  ])('returns the very same array when the move goes %s', (_case, from, to) => {
    const order = ['a', 'b', 'c'];

    expect(moveItem(order, from, to)).toBe(order);
  });
});
