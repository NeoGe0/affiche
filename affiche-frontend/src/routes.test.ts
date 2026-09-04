import { describe, expect, it } from 'vitest';

import { libraryPath, listingPath, parseLocation } from './routes';

describe('listingPath', () => {
  it('names a single library', () => {
    expect(libraryPath(1, 5)).toBe('/servers/1/libraries/5');
  });

  it('uses the sentinel for the merged "All Libraries" listing', () => {
    expect(libraryPath(1)).toBe('/servers/1/libraries/all');
  });

  it('hangs an item off the listing it was opened from', () => {
    expect(libraryPath(1, 5, 10)).toBe('/servers/1/libraries/5/items/10');
  });

  it('keeps the same shape for the other two views', () => {
    expect(listingPath('trash', 1, 5)).toBe('/servers/1/trash/5');
    expect(listingPath('collections', 1)).toBe('/servers/1/collections/all');
  });
});

describe('parseLocation', () => {
  it('round-trips every path the builder produces', () => {
    expect(parseLocation(libraryPath(1, 5))).toEqual(
      { serverId: 1, libraryId: 5, view: 'library', itemId: undefined });
    expect(parseLocation(libraryPath(1, 5, 10))).toEqual(
      { serverId: 1, libraryId: 5, view: 'library', itemId: 10 });
    expect(parseLocation(listingPath('trash', 2, 7))).toEqual(
      { serverId: 2, libraryId: 7, view: 'trash', itemId: undefined });
    expect(parseLocation(listingPath('collections', 2, 7))).toEqual(
      { serverId: 2, libraryId: 7, view: 'collections', itemId: undefined });
  });

  it('reads the sentinel as "no library chosen"', () => {
    expect(parseLocation(libraryPath(1))).toMatchObject({ serverId: 1, libraryId: undefined });
  });

  it('falls back to the library view for a path it does not recognise', () => {
    expect(parseLocation('/settings')).toEqual({ view: 'library' });
    expect(parseLocation('/')).toEqual({ view: 'library' });
  });

  it('ignores ids that are not positive integers', () => {

    expect(parseLocation('/servers/x/libraries/y')).toMatchObject(
      { serverId: undefined, libraryId: undefined, view: 'library' });
  });
});
