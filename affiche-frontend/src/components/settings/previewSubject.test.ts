import { describe, expect, it } from 'vitest';

import {
  libraryOptions,
  parsePreviewSubject,
  previewSubjectFromItem,
  serializePreviewSubject,
  type PreviewSubject,
} from './previewSubject';
import type { Library, LibraryItem } from '../../types';

function makeLibrary(id: number, mediaServerId: number, name: string): Library {
  return { id, media_server_id: mediaServerId, name, library_type: 'movie' };
}

function makeItem(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    id: 7,
    library_id: 3,
    title: 'Arrival',
    type: 'movie',
    year: 2016,
    processed: false,
    locked: false,
    ...overrides,
  };
}

describe('previewSubjectFromItem', () => {
  it('carries the ids the preview needs alongside the artwork target', () => {
    const subject = previewSubjectFromItem(makeItem({ tmdb_id: '329865' }));

    expect(subject).toEqual({
      libraryId: 3,
      itemId: 7,
      title: 'Arrival',
      year: 2016,
      mediaType: 'movie',
      tmdbId: 329865,
      tvdbId: undefined,
    });
  });

  it('treats anything that is not a movie as a show', () => {
    expect(previewSubjectFromItem(makeItem({ type: 'series' })).mediaType).toBe('show');
  });
});

describe('libraryOptions', () => {
  const plex = { id: 1, name: 'Plex' };
  const jellyfin = { id: 2, name: 'Jellyfin' };

  it('leaves the server name out when there is only one server', () => {
    const options = libraryOptions([plex], [makeLibrary(10, 1, 'Movies')]);

    expect(options).toEqual([{ id: 10, mediaServerId: 1, label: 'Movies' }]);
  });

  it('qualifies labels with the server name once there are several', () => {
    const options = libraryOptions(
      [plex, jellyfin],
      [makeLibrary(10, 1, 'Movies'), makeLibrary(20, 2, 'Movies')]
    );

    expect(options.map((o) => o.label)).toEqual(['Plex · Movies', 'Jellyfin · Movies']);
  });

  it('drops libraries whose server is not in the list', () => {
    expect(libraryOptions([plex], [makeLibrary(30, 99, 'Orphan')])).toEqual([]);
  });
});

describe('parsePreviewSubject', () => {
  const subject: PreviewSubject = {
    libraryId: 3,
    itemId: 7,
    title: 'Arrival',
    year: 2016,
    mediaType: 'movie',
    tmdbId: 329865,
    tvdbId: undefined,
  };

  it('round-trips a serialized subject', () => {
    expect(parsePreviewSubject(serializePreviewSubject(subject))).toEqual(subject);
  });

  it('returns null for nothing stored', () => {
    expect(parsePreviewSubject(null)).toBeNull();
    expect(parsePreviewSubject('')).toBeNull();
  });

  it('returns null rather than throwing on malformed JSON', () => {
    expect(parsePreviewSubject('{not json')).toBeNull();
  });

  it.each([
    ['a missing title', { libraryId: 3, itemId: 7, mediaType: 'movie' }],
    ['an empty title', { libraryId: 3, itemId: 7, title: '', mediaType: 'movie' }],
    ['ids of the wrong type', { libraryId: '3', itemId: 7, title: 'Arrival', mediaType: 'movie' }],
    ['an unknown media type', { libraryId: 3, itemId: 7, title: 'Arrival', mediaType: 'album' }],
    ['a non-object', 42],
  ])('rejects %s', (_label, stored) => {
    expect(parsePreviewSubject(JSON.stringify(stored))).toBeNull();
  });

  it('drops optional fields that are not finite numbers instead of rejecting the subject', () => {
    const stored = JSON.stringify({
      libraryId: 3,
      itemId: 7,
      title: 'Arrival',
      mediaType: 'movie',
      year: 'MMXVI',
      tmdbId: null,
    });

    expect(parsePreviewSubject(stored)).toEqual({
      libraryId: 3,
      itemId: 7,
      title: 'Arrival',
      mediaType: 'movie',
      year: undefined,
      tmdbId: undefined,
      tvdbId: undefined,
    });
  });
});
