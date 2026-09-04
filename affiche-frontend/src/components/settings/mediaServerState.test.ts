import { describe, expect, it } from 'vitest';

import {
  decomposeInterval,
  defaultLibrarySettings,
  intervalToMinutes,
  patchLibrarySettings,
  replaceServer,
  toLibrarySettingsUpdate,
  toggleId,
  webhookUrl,
  withoutIds,
  type ServerWithLibraries,
} from './mediaServerState';
import type { Library, LibrarySettings, MediaServerResponse } from '../../types';

const server = (id: number, overrides: Partial<MediaServerResponse> = {}) =>
  ({
    id,
    name: `server-${id}`,
    type: 'PLEX',
    url: 'http://localhost:32400',
    enabled: true,
    webhook_enabled: false,
    webhook_token: null,
    last_sync: null,
    created_at: '',
    updated_at: '',
    ...overrides,
  }) as MediaServerResponse;

const library = (id: number) =>
  ({ id, media_server_id: 1, name: `library-${id}`, library_type: 'movie' }) as Library;

const tree = (): ServerWithLibraries[] => [
  {
    server: server(1),
    libraries: [
      { library: library(10), settings: defaultLibrarySettings(10) },
      { library: library(11), settings: defaultLibrarySettings(11) },
    ],
  },
  {
    server: server(2),
    libraries: [{ library: library(20), settings: defaultLibrarySettings(20) }],
  },
];

describe('decomposeInterval', () => {
  it('shows a day-aligned interval in days', () => {
    expect(decomposeInterval(2880)).toEqual({ value: 2, unit: 'days' });
  });

  it('shows anything else in hours', () => {
    expect(decomposeInterval(360)).toEqual({ value: 6, unit: 'hours' });
  });

  it('never falls below one hour, so the number input keeps a valid value', () => {
    expect(decomposeInterval(0)).toEqual({ value: 1, unit: 'hours' });
    expect(decomposeInterval(5)).toEqual({ value: 1, unit: 'hours' });
  });
});

describe('intervalToMinutes', () => {
  it('round-trips with decomposeInterval', () => {
    const { value, unit } = decomposeInterval(4320);

    expect(intervalToMinutes(value, unit)).toBe(4320);
  });

  it('clamps a cleared or negative input to one unit', () => {
    expect(intervalToMinutes(0, 'hours')).toBe(60);
    expect(intervalToMinutes(-3, 'days')).toBe(1440);
  });
});

describe('webhookUrl', () => {
  it('builds the inbound URL under the app prefix', () => {
    expect(webhookUrl('https://affiche.example', 'abc123')).toBe(
      'https://affiche.example/affiche/webhooks/abc123'
    );
  });
});

describe('patchLibrarySettings', () => {
  it('applies the patch to the targeted library only', () => {
    const next = patchLibrarySettings(tree(), 1, 11, { enabled: false });

    expect(next[0].libraries[1].settings.enabled).toBe(false);
    expect(next[0].libraries[0].settings.enabled).toBe(true);
    expect(next[1].libraries[0].settings.enabled).toBe(true);
  });

  it('merges rather than replaces the settings', () => {
    const next = patchLibrarySettings(tree(), 1, 10, { auto_sync_enabled: true });

    expect(next[0].libraries[0].settings.provider_order).toEqual(
      defaultLibrarySettings(10).provider_order
    );
  });

  it('leaves the previous tree untouched', () => {
    const before = tree();

    patchLibrarySettings(before, 1, 10, { enabled: false });

    expect(before[0].libraries[0].settings.enabled).toBe(true);
  });

  it('keeps untouched servers referentially equal', () => {
    const before = tree();
    const next = patchLibrarySettings(before, 1, 10, { enabled: false });

    expect(next[1]).toBe(before[1]);
  });

  it('is a no-op when the ids match nothing', () => {
    const before = tree();
    const next = patchLibrarySettings(before, 99, 10, { enabled: false });

    expect(next).toEqual(before);
  });
});

describe('replaceServer', () => {
  it('swaps the server record and keeps its libraries', () => {
    const before = tree();
    const next = replaceServer(before, server(1, { webhook_enabled: true, webhook_token: 'tok' }));

    expect(next[0].server.webhook_token).toBe('tok');
    expect(next[0].libraries).toBe(before[0].libraries);
    expect(next[1]).toBe(before[1]);
  });
});

describe('toLibrarySettingsUpdate', () => {
  it('drops the server-owned fields from the PATCH body', () => {
    const settings: LibrarySettings = {
      ...defaultLibrarySettings(10),
      last_auto_sync_at: '2026-07-27T10:00:00Z',
      last_full_sync_at: '2026-07-27T10:00:00Z',
    };

    const body = toLibrarySettingsUpdate(settings);

    expect(body).not.toHaveProperty('library_id');
    expect(body).not.toHaveProperty('last_auto_sync_at');
    expect(body).not.toHaveProperty('last_full_sync_at');
  });

  it('carries every editable field', () => {
    const body = toLibrarySettingsUpdate({
      ...defaultLibrarySettings(10),
      enabled: false,
      upload_enabled: false,
      provider_order: ['fanart'],
      track_episodes: true,
      track_collections: true,
      auto_sync_enabled: true,
      auto_sync_interval_minutes: 1440,
      auto_pickup_action: 'upload',
      overlay_options: { border_px: 42 },
      text_options: { all_caps: true },
      style_profile_id: null,
    });

    expect(body).toEqual({
      enabled: false,
      upload_enabled: false,
      provider_order: ['fanart'],
      track_episodes: true,
      track_collections: true,
      auto_sync_enabled: true,
      auto_sync_interval_minutes: 1440,
      auto_pickup_action: 'upload',
      overlay_options: { border_px: 42 },
      text_options: { all_caps: true },
      style_profile_id: null,
    });
  });

  it('sends an explicit null for a library that inherits the global style', () => {

    const body = toLibrarySettingsUpdate(defaultLibrarySettings(10));

    expect(body.overlay_options).toBeNull();
    expect(body.text_options).toBeNull();
  });
});

describe('set helpers', () => {
  it('withoutIds clears the given ids without mutating the source', () => {
    const before = new Set([1, 2, 3]);

    expect([...withoutIds(before, [1, 3])]).toEqual([2]);
    expect([...before]).toEqual([1, 2, 3]);
  });

  it('toggleId adds then removes, without mutating the source', () => {
    const before = new Set([1]);

    expect([...toggleId(before, 2)]).toEqual([1, 2]);
    expect([...toggleId(before, 1)]).toEqual([]);
    expect([...before]).toEqual([1]);
  });
});
