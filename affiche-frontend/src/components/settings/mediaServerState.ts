import type {
  Library,
  LibrarySettings,
  MediaServerResponse,
} from '../../types';
import type { LibrarySettingsUpdate } from '../../api/libraries';

export interface LibraryWithSettings {
  library: Library;
  settings: LibrarySettings;
}

export interface ServerWithLibraries {
  server: MediaServerResponse;
  libraries: LibraryWithSettings[];
}

export function defaultLibrarySettings(libraryId: number): LibrarySettings {
  return {
    library_id: libraryId,
    enabled: true,
    upload_enabled: true,
    provider_order: ['tmdb', 'tvdb', 'fanart', 'mediux', 'tvmaze', 'shoko'],
    track_episodes: false,
  track_collections: false,
    auto_sync_enabled: false,
    auto_sync_interval_minutes: 360,
    auto_pickup_action: 'sync',
    last_auto_sync_at: null,
    last_full_sync_at: null,
  };
}

export type IntervalUnit = 'hours' | 'days';

export const UNIT_MINUTES: Record<IntervalUnit, number> = { hours: 60, days: 1440 };

export function decomposeInterval(minutes: number): { value: number; unit: IntervalUnit } {
  if (minutes > 0 && minutes % UNIT_MINUTES.days === 0) {
    return { value: minutes / UNIT_MINUTES.days, unit: 'days' };
  }
  return { value: Math.max(1, Math.round(minutes / UNIT_MINUTES.hours)), unit: 'hours' };
}

export function intervalToMinutes(value: number, unit: IntervalUnit): number {
  return Math.max(1, Math.round(value)) * UNIT_MINUTES[unit];
}

export function webhookUrl(origin: string, token: string): string {
  return `${origin}/affiche/webhooks/${token}`;
}

export function patchLibrarySettings(
  servers: ServerWithLibraries[],
  serverId: number,
  libraryId: number,
  patch: Partial<LibrarySettings>
): ServerWithLibraries[] {
  return servers.map((entry) =>
    entry.server.id === serverId
      ? {
          ...entry,
          libraries: entry.libraries.map((lib) =>
            lib.library.id === libraryId
              ? { ...lib, settings: { ...lib.settings, ...patch } }
              : lib
          ),
        }
      : entry
  );
}

export function patchServer(
  servers: ServerWithLibraries[],
  serverId: number,
  patch: Partial<MediaServerResponse>
): ServerWithLibraries[] {
  return servers.map((entry) =>
    entry.server.id === serverId
      ? { ...entry, server: { ...entry.server, ...patch } }
      : entry
  );
}

export function replaceServer(
  servers: ServerWithLibraries[],
  updated: MediaServerResponse
): ServerWithLibraries[] {
  return servers.map((entry) =>
    entry.server.id === updated.id ? { ...entry, server: updated } : entry
  );
}

export function toLibrarySettingsUpdate(settings: LibrarySettings): LibrarySettingsUpdate {
  return {
    enabled: settings.enabled,
    upload_enabled: settings.upload_enabled,
    provider_order: settings.provider_order,
    track_episodes: settings.track_episodes,
    track_collections: settings.track_collections,
    auto_sync_enabled: settings.auto_sync_enabled,
    auto_sync_interval_minutes: settings.auto_sync_interval_minutes,
    auto_pickup_action: settings.auto_pickup_action,

    overlay_options: settings.overlay_options ?? null,
    text_options: settings.text_options ?? null,
    style_profile_id: settings.style_profile_id ?? null,
  };
}

export function withoutIds(ids: Set<number>, removed: number[]): Set<number> {
  const next = new Set(ids);
  removed.forEach((id) => next.delete(id));
  return next;
}

export function toggleId(ids: Set<number>, id: number): Set<number> {
  const next = new Set(ids);
  if (!next.delete(id)) next.add(id);
  return next;
}
