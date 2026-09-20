import { describe, expect, it } from 'vitest';

import { emptySelection, neighbours, pruneSelection, selectRange, toggleAll, toggleId } from './selection';

const items = (...ids: number[]) => ids.map((id) => ({ id }));
const set = (...ids: number[]) => new Set(ids);

describe('toggleId', () => {
  it('adds an id that was not selected', () => {
    expect([...toggleId(set(1), 2)].sort()).toEqual([1, 2]);
  });

  it('removes one that was', () => {
    expect([...toggleId(set(1, 2), 1)]).toEqual([2]);
  });

  it('does not mutate the set it was given', () => {
    const before = set(1);
    toggleId(before, 2);
    expect([...before]).toEqual([1]);
  });
});

describe('toggleAll', () => {
  it('selects every listed item', () => {
    expect([...toggleAll(emptySelection(), items(1, 2, 3))].sort()).toEqual([1, 2, 3]);
  });

  it('clears when everything listed is already selected', () => {
    expect([...toggleAll(set(1, 2), items(1, 2))]).toEqual([]);
  });

  it('selects all when only some are selected', () => {
    expect([...toggleAll(set(1), items(1, 2))].sort()).toEqual([1, 2]);
  });

  it('judges "all" against what is listed, not the whole library', () => {

    expect([...toggleAll(set(1, 2, 99), items(1, 2))]).toEqual([]);
  });

  it('does not clear on an empty listing', () => {

    expect([...toggleAll(emptySelection(), [])]).toEqual([]);
  });
});

describe('pruneSelection', () => {
  it('drops ids that are no longer listed', () => {
    expect([...pruneSelection(set(1, 2, 3), items(1, 3))].sort()).toEqual([1, 3]);
  });

  it('returns the very same set when nothing was dropped', () => {

    const selected = set(1, 2);

    expect(pruneSelection(selected, items(1, 2, 3))).toBe(selected);
  });

  it('returns the same set when there is nothing selected', () => {
    const selected = emptySelection();

    expect(pruneSelection(selected, items(1))).toBe(selected);
  });

  it('clears the selection when the listing empties', () => {

    expect([...pruneSelection(set(1, 2), [])]).toEqual([]);
  });
});

describe('selectRange', () => {
  it('adds everything between the anchor and the target, in either direction', () => {
    expect([...selectRange(set(), items(1, 2, 3, 4, 5), 2, 4)].sort()).toEqual([2, 3, 4]);
    expect([...selectRange(set(), items(1, 2, 3, 4, 5), 4, 2)].sort()).toEqual([2, 3, 4]);
  });

  it('keeps what was already selected outside the range', () => {
    expect([...selectRange(set(5), items(1, 2, 3, 4, 5), 1, 2)].sort()).toEqual([1, 2, 5]);
  });

  it('falls back to a plain toggle without a listed anchor', () => {
    expect([...selectRange(set(), items(1, 2, 3), null, 2)]).toEqual([2]);
    expect([...selectRange(set(), items(1, 2, 3), 99, 2)]).toEqual([2]);
  });
});

describe('neighbours', () => {
  const listed = [{ id: 1, library_id: 1 }, { id: 2, library_id: 1 }, { id: 3, library_id: 1 }];

  it('finds the items either side', () => {
    expect(neighbours(listed, { id: 2, library_id: 1 })).toEqual({ previous: listed[0], next: listed[2] });
  });

  it('has nothing past the ends, or for an item that is not listed', () => {
    expect(neighbours(listed, { id: 1 }).previous).toBeUndefined();
    expect(neighbours(listed, { id: 3 }).next).toBeUndefined();
    expect(neighbours(listed, { id: 9 })).toEqual({});
  });
});
