import { describe, expect, it } from 'vitest';

import { activeFilterChips } from './listingFilters';
import { NO_PROVIDER } from '../../types';

describe('activeFilterChips', () => {
  it('summarises nothing when neither dimension is narrowed', () => {
    expect(activeFilterChips('all', undefined)).toEqual([]);
  });

  it('treats an empty provider as "any source" rather than a filter', () => {
    expect(activeFilterChips('all', '')).toEqual([]);
  });

  it('names the status bucket with the same wording the panel uses', () => {
    expect(activeFilterChips('errors', undefined)).toEqual([
      { facet: 'status', label: 'With errors' },
    ]);
  });

  it('names both dimensions when both are narrowed, status first', () => {
    expect(activeFilterChips('unprocessed', 'tmdb')).toEqual([
      { facet: 'status', label: 'Unprocessed' },
      { facet: 'source', label: 'TMDB' },
    ]);
  });

  it('spells out the no-provenance bucket, which has no provider name of its own', () => {
    expect(activeFilterChips('all', NO_PROVIDER)).toEqual([
      { facet: 'source', label: 'No source recorded' },
    ]);
  });
});
