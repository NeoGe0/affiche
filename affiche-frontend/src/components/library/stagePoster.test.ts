import { describe, expect, it } from 'vitest';

import type { LibraryItem } from '../../types';
import { isNewArrival, newestWithPoster } from './stagePoster';

const item = (overrides: Partial<LibraryItem> & { id: number }): LibraryItem =>
  ({ library_id: 2, title: `Item ${overrides.id}`, type: 'movie', processed: false, locked: false, ...overrides });

describe('newestWithPoster', () => {
  it('skips items that have nothing to show', () => {
    const stage = newestWithPoster([
      item({ id: 1 }),
      item({ id: 2, processed: true, has_poster: true, poster_version: 'v3' }),
    ]);

    expect(stage).toEqual({ libraryId: 2, itemId: 2, title: 'Item 2', posterVersion: 'v3', reason: 'newest' });
  });

  it('counts a live poster version as a poster even before has_poster is set', () => {
    expect(newestWithPoster([item({ id: 5, processed: true, poster_version: 'v1' })])?.itemId).toBe(5);
  });

  it("passes over the server's own artwork on an item Affiche has not processed", () => {
    expect(newestWithPoster([item({ id: 3, has_poster: true, poster_version: 'v1' })])).toBeNull();
  });

  it('has nothing to stage when no item has a poster', () => {
    expect(newestWithPoster([item({ id: 1 })])).toBeNull();
  });
});

describe('isNewArrival', () => {
  const onStage = { libraryId: 2, itemId: 9, title: 'Alien', posterVersion: 'v1', reason: 'generated' as const };

  it('ignores a repeat of the poster already on stage', () => {
    expect(isNewArrival(onStage, { libraryId: 2, itemId: 9, posterVersion: 'v1', reason: 'generated' })).toBe(false);
  });

  it('takes a new version of the same item, and any other item', () => {
    expect(isNewArrival(onStage, { libraryId: 2, itemId: 9, posterVersion: 'v2', reason: 'generated' })).toBe(true);
    expect(isNewArrival(onStage, { libraryId: 2, itemId: 10, posterVersion: 'v1', reason: 'generated' })).toBe(true);
    expect(isNewArrival(null, { libraryId: 2, itemId: 10, posterVersion: 'v1', reason: 'generated' })).toBe(true);
  });
});
