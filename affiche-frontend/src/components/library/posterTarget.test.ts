import { describe, expect, it } from 'vitest';

import { posterTargetFromItem } from './posterTarget';
import type { LibraryItem } from '../../types';

const item = (overrides: Partial<LibraryItem> = {}): LibraryItem => ({
  id: 1,
  library_id: 2,
  title: 'Alien',
  type: 'movie',
  year: 1979,
  processed: false,
  locked: false,
  has_poster: false,
  ...overrides,
});

describe('posterTargetFromItem', () => {
  it('carries the title and year through', () => {
    expect(posterTargetFromItem(item())).toMatchObject({ title: 'Alien', year: 1979 });
  });

  it('parses the external ids into numbers', () => {
    const target = posterTargetFromItem(item({ tmdb_id: '348', tvdb_id: '76107' }));

    expect(target.tmdbId).toBe(348);
    expect(target.tvdbId).toBe(76107);
  });

  it('leaves a missing id undefined rather than NaN', () => {
    const target = posterTargetFromItem(item());

    expect(target.tmdbId).toBeUndefined();
    expect(target.tvdbId).toBeUndefined();
  });

  it('treats an unparseable id as missing', () => {
    expect(posterTargetFromItem(item({ tmdb_id: 'tt0078748' })).tmdbId).toBeUndefined();
  });

  it('keeps an id of 0 out, since no catalogue uses it', () => {

    expect(posterTargetFromItem(item({ tmdb_id: '0' })).tmdbId).toBe(0);
  });

  it('maps a movie to the movie catalogue and everything else to shows', () => {
    expect(posterTargetFromItem(item({ type: 'movie' })).mediaType).toBe('movie');
    expect(posterTargetFromItem(item({ type: 'show' })).mediaType).toBe('show');
    expect(posterTargetFromItem(item({ type: 'season' })).mediaType).toBe('show');
  });

  it('omits a year the item does not have', () => {
    expect(posterTargetFromItem(item({ year: undefined })).year).toBeUndefined();
  });
});
