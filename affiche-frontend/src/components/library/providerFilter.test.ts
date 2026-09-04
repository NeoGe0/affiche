import { describe, expect, it } from 'vitest';

import { NO_PROVIDER } from '../../types';
import { providerFilterOptions } from './providerFilter';

const values = (providers?: Record<string, number>, selected?: string) =>
  providerFilterOptions(providers, selected).map((o) => o.value);

describe('providerFilterOptions', () => {
  it('offers only the provenances the library actually holds', () => {
    expect(values({ tmdb: 3, mediux: 1 })).toEqual(['', 'tmdb', 'mediux']);
  });

  it('orders providers by how many posters they produced', () => {
    expect(values({ mediux: 1, tmdb: 9, fanart: 4 })).toEqual(['', 'tmdb', 'fanart', 'mediux']);
  });

  it('ties break alphabetically, so the list does not reshuffle between equal counts', () => {
    expect(values({ tmdb: 2, fanart: 2 })).toEqual(['', 'fanart', 'tmdb']);
  });

  it('keeps "no source recorded" last however large it is', () => {
    expect(values({ [NO_PROVIDER]: 900, tmdb: 2 })).toEqual(['', 'tmdb', NO_PROVIDER]);
  });

  it('labels the sentinels rather than showing their slugs', () => {
    const labels = providerFilterOptions({ server: 1, manual: 1, [NO_PROVIDER]: 1, tmdb: 1 })
      .map((o) => o.label);

    expect(labels).toEqual([
      'Any source', 'Chosen manually', 'Media server artwork', 'TMDB', 'No source recorded',
    ]);
  });

  it('counts "any source" as the sum of the buckets', () => {
    expect(providerFilterOptions({ tmdb: 3, mediux: 1 })[0].count).toBe(4);
  });

  it('leaves every count unknown while the buckets are still loading', () => {
    const options = providerFilterOptions(undefined);

    expect(options).toEqual([{ value: '', label: 'Any source', count: undefined }]);
  });

  it('keeps the active provider listed when the counts do not carry it', () => {

    expect(values({ tmdb: 3 }, 'mediux')).toEqual(['', 'tmdb', 'mediux']);
    expect(values(undefined, 'mediux')).toEqual(['', 'mediux']);
  });

  it('does not duplicate the active provider when the counts do carry it', () => {
    expect(values({ tmdb: 3, mediux: 1 }, 'mediux')).toEqual(['', 'tmdb', 'mediux']);
  });
});
