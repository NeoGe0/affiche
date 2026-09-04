import { describe, expect, it } from 'vitest';

import { emptySelection, pruneSelection, toggleAll, toggleId } from './selection';

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
