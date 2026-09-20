import { describe, expect, it } from 'vitest';

import type { LibraryItem } from '../../types';
import { detailsSummary, posterState, primaryPosterAction } from './posterState';

const item = (overrides: Partial<LibraryItem> = {}): LibraryItem =>
  ({ id: 1, library_id: 1, title: 'Alien', type: 'movie', processed: false, locked: false, ...overrides });

describe('posterState', () => {
  it('puts a failure ahead of everything, since it is what needs attention', () => {
    expect(posterState(item({ processed: true, poster_uploaded_at: '2026-09-01', error_message: 'x' })))
      .toBe('failed');
  });

  it('tells an uploaded poster from one that is only generated', () => {
    expect(posterState(item({ processed: true, poster_uploaded_at: '2026-09-01' }))).toBe('uploaded');
    expect(posterState(item({ processed: true }))).toBe('ready');
    expect(posterState(item())).toBe('pending');
  });
});

describe('primaryPosterAction', () => {
  it('offers upload for a generated poster that has not reached the server', () => {
    expect(primaryPosterAction(item({ processed: true }))).toBe('upload');
  });

  it('offers upload on a locked item too, since the lock only stops generation', () => {
    expect(primaryPosterAction(item({ processed: true, locked: true }))).toBe('upload');
  });

  it('offers generation for a pending item, but not a locked one', () => {
    expect(primaryPosterAction(item())).toBe('generate');
    expect(primaryPosterAction(item({ locked: true }))).toBeNull();
  });

  it('sends a failed item to choosing artwork by hand', () => {
    expect(primaryPosterAction(item({ error_message: 'No poster found' }))).toBe('choose');
  });

  it('fills nothing in once the poster is on the server', () => {
    expect(primaryPosterAction(item({ processed: true, poster_uploaded_at: '2026-09-01' }))).toBeNull();
  });
});

describe('detailsSummary', () => {
  it('joins the parts of the file it knows and skips the rest', () => {
    expect(detailsSummary(item({ media_resolution: '4k', video_codec: 'hevc', media_container: 'mkv' })))
      .toBe('4k · HEVC · MKV');
  });

  it('names what the block holds when there is no file information', () => {
    expect(detailsSummary(item())).toBe('IDs and dates');
  });
});
