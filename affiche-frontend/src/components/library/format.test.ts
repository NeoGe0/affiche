import { describe, expect, it } from 'vitest';

import type { LibraryItem } from '../../types';
import {
  formatAudio,
  formatBitrate,
  formatChannels,
  formatDate,
  formatDateTime,
  formatFileSize,
  canReset,
  failureTooltip,
  hasQuality,
  posterSource,
  posterStatus,
} from './format';

const DASH = '—';

const item = (overrides: Partial<LibraryItem> = {}): LibraryItem =>
  ({
    id: 1,
    library_id: 1,
    title: 'Arrival',
    type: 'movie',
    processed: false,
    has_poster: false,
    ...overrides,
  }) as LibraryItem;

describe('formatDateTime / formatDate', () => {
  it('render an em-dash when there is no timestamp', () => {
    expect(formatDateTime(undefined)).toBe(DASH);
    expect(formatDateTime(null)).toBe(DASH);
    expect(formatDateTime('')).toBe(DASH);
    expect(formatDate(undefined)).toBe(DASH);
    expect(formatDate(null)).toBe(DASH);
  });

  it('render an em-dash for an unparseable timestamp', () => {
    expect(formatDateTime('not a date')).toBe(DASH);
    expect(formatDate('2024-13-45')).toBe(DASH);
  });

  it('render a real timestamp, locale permitting', () => {
    expect(formatDateTime('2024-03-15T10:30:00Z')).toContain('2024');
    expect(formatDate('2024-03-15T10:30:00Z')).toContain('2024');
  });

  it('drop the time of day from the date-only variant', () => {

    expect(formatDate('2024-03-15T10:30:00Z')).not.toMatch(/\d{1,2}:\d{2}/);
  });
});

describe('formatFileSize', () => {
  it('switches to GB at one gibibyte, with two decimals', () => {
    expect(formatFileSize(1024 ** 3)).toBe('1.00 GB');
    expect(formatFileSize(1.5 * 1024 ** 3)).toBe('1.50 GB');
    expect(formatFileSize(12 * 1024 ** 3)).toBe('12.00 GB');
  });

  it('stays in whole MB below a gibibyte', () => {
    expect(formatFileSize(500 * 1024 ** 2)).toBe('500 MB');
    expect(formatFileSize(1024 ** 3 - 1)).toBe('1024 MB');
  });

  it('renders an em-dash for a missing or zero size', () => {
    expect(formatFileSize(undefined)).toBe(DASH);
    expect(formatFileSize(null)).toBe(DASH);
    expect(formatFileSize(0)).toBe(DASH);
  });
});

describe('formatBitrate', () => {
  it('renders Mbps with one decimal', () => {
    expect(formatBitrate(8_000_000)).toBe('8.0 Mbps');
    expect(formatBitrate(2_500_000)).toBe('2.5 Mbps');
  });

  it('renders an em-dash for a missing or zero bitrate', () => {
    expect(formatBitrate(undefined)).toBe(DASH);
    expect(formatBitrate(null)).toBe(DASH);
    expect(formatBitrate(0)).toBe(DASH);
  });
});

describe('formatChannels', () => {
  it('maps known channel counts to their layout label', () => {
    expect(formatChannels(1)).toBe('1.0');
    expect(formatChannels(2)).toBe('2.0');
    expect(formatChannels(6)).toBe('5.1');
    expect(formatChannels(7)).toBe('6.1');
    expect(formatChannels(8)).toBe('7.1');
  });

  it('falls back to a raw count for an unmapped layout', () => {
    expect(formatChannels(3)).toBe('3ch');
    expect(formatChannels(12)).toBe('12ch');
  });

  it('returns null when the count is unknown', () => {
    expect(formatChannels(undefined)).toBeNull();
    expect(formatChannels(null)).toBeNull();
    expect(formatChannels(0)).toBeNull();
  });
});

describe('formatAudio', () => {
  it('joins codec and layout', () => {
    expect(formatAudio(item({ audio_codec: 'eac3', audio_channels: 6 }))).toBe('EAC3 · 5.1');
  });

  it('drops whichever part is missing', () => {
    expect(formatAudio(item({ audio_codec: 'aac' }))).toBe('AAC');
    expect(formatAudio(item({ audio_channels: 2 }))).toBe('2.0');
  });

  it('renders an em-dash when neither is known', () => {
    expect(formatAudio(item())).toBe(DASH);
  });
});

describe('posterStatus', () => {

  it('reports an upload with its timestamp', () => {
    expect(posterStatus(item({ poster_uploaded_at: '2024-03-15T10:30:00Z', processed: true })))
      .toMatch(/^Uploaded /);
  });

  it('reports a generated poster that has not been uploaded', () => {
    expect(posterStatus(item({ processed: true }))).toBe('Generated (not uploaded)');

    expect(posterStatus(item({ has_poster: true }))).toBe('Generated (not uploaded)');
  });

  it('reports nothing stored', () => {
    expect(posterStatus(item())).toBe('None');
  });
});

describe('hasQuality', () => {
  it('is true when any media field is present', () => {
    expect(hasQuality(item({ media_resolution: '1080p' }))).toBe(true);
    expect(hasQuality(item({ media_height: 1080 }))).toBe(true);
    expect(hasQuality(item({ video_codec: 'hevc' }))).toBe(true);
    expect(hasQuality(item({ media_container: 'mkv' }))).toBe(true);
    expect(hasQuality(item({ media_size_bytes: 1024 }))).toBe(true);
  });

  it('is false when none is', () => {
    expect(hasQuality(item({ type: 'show' }))).toBe(false);
  });

  it('is not opened by audio fields alone', () => {
    expect(hasQuality(item({ audio_codec: 'eac3', audio_channels: 6 }))).toBe(false);
  });
});

describe('posterSource', () => {
  it('names the provider that produced the poster', () => {
    expect(posterSource('tmdb')).toBe('TMDB');
    expect(posterSource('shoko')).toBe('Shoko');
  });

  it('spells out the two sentinels rather than showing them raw', () => {

    expect(posterSource('server')).toBe('Media server artwork');
    expect(posterSource('manual')).toBe('Chosen manually');
  });

  it('renders an em-dash when nothing was recorded', () => {

    expect(posterSource(null)).toBe('—');
    expect(posterSource(undefined)).toBe('—');
  });

  it('falls back to the slug for a provider it has no label for', () => {
    expect(posterSource('somethingnew')).toBe('somethingnew');
  });
});

describe('canReset', () => {
  const item = (overrides: Partial<LibraryItem>): LibraryItem =>
    ({ id: 1, library_id: 1, title: 'T', type: 'movie', processed: false, locked: false,
       ...overrides });

  it('allows resetting a failed item', () => {

    expect(canReset(item({ error_message: 'No poster found' }))).toBe(true);
  });

  it('allows resetting a processed item', () => {
    expect(canReset(item({ processed: true }))).toBe(true);
  });

  it('refuses an item Affiche never touched', () => {
    expect(canReset(item({}))).toBe(false);
  });
});

describe('failureTooltip', () => {
  const item = (overrides: Partial<LibraryItem>): LibraryItem =>
    ({ id: 1, library_id: 1, title: 'T', type: 'movie', processed: false, locked: false,
       ...overrides });

  it('appends the diagnosis when the server named a cause', () => {
    const tip = failureTooltip(item({
      error_message: 'No poster found', error_cause: 'identifier_mismatch',
    }));
    expect(tip).toContain('No poster found');
    expect(tip).toContain('IMDb or TVDB');
  });

  it('is just the error for a cause this build has no copy for', () => {

    expect(failureTooltip(item({ error_message: 'No poster found', error_cause: 'from_the_future' })))
      .toBe('No poster found');
  });

  it('is just the error when there is no cause', () => {
    expect(failureTooltip(item({ error_message: 'No poster found' }))).toBe('No poster found');
  });

  it('is absent for an item that did not fail', () => {
    expect(failureTooltip(item({}))).toBeUndefined();
  });
});
