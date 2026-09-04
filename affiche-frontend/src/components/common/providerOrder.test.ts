import { describe, expect, it } from 'vitest';

import { reconcileProviderOrder } from './providerOrder';

describe('reconcileProviderOrder', () => {
  it('keeps the saved ranking', () => {
    expect(reconcileProviderOrder(['fanart', 'tmdb'], ['tmdb', 'fanart'])).toEqual([
      'fanart',
      'tmdb',
    ]);
  });

  it('drops a provider that was removed', () => {
    expect(reconcileProviderOrder(['tmdb', 'tvdb', 'fanart'], ['tmdb', 'fanart'])).toEqual([
      'tmdb',
      'fanart',
    ]);
  });

  it('appends a newly added provider, which no saved order can mention', () => {
    expect(reconcileProviderOrder(['tmdb'], ['tmdb', 'shoko'])).toEqual(['tmdb', 'shoko']);
  });

  it('never duplicates when the saved order already lists everything', () => {
    expect(reconcileProviderOrder(['tmdb', 'tmdb'], ['tmdb'])).toEqual(['tmdb']);
  });

  it('is empty while nothing is added, rather than echoing the saved order', () => {
    expect(reconcileProviderOrder(['tmdb', 'tvdb'], [])).toEqual([]);
  });
});
