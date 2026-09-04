import { api, API_BASE } from './client';
import type { AlphaIndexEntry, AutoPickupAction, LibraryItemCounts, ItemEpisode, ItemStatusFilter, Library, LibraryItem, LibraryItemWithSeasons, LibrarySettings, LibraryStyleStaleness, PaginatedLibraryItems, SyncTaskResponse } from '../types';

export interface LibrarySettingsUpdate {
  enabled?: boolean;
  upload_enabled?: boolean;
  provider_order?: string[];

  overlay_options?: Record<string, unknown> | null;
  text_options?: Record<string, unknown> | null;
  style_profile_id?: number | null;
  track_episodes?: boolean;
  track_collections?: boolean;
  auto_sync_enabled?: boolean;
  auto_sync_interval_minutes?: number;
  auto_pickup_action?: AutoPickupAction;
}

export type PosterSize = 'full' | 'thumb';

export type PosterVariant = 'generated' | 'source';

function posterQuery(
  version?: string | null,
  size: PosterSize = 'full',
  variant: PosterVariant = 'generated'
): string {
  const params = new URLSearchParams();
  if (version) params.set('v', version);
  if (size !== 'full') params.set('size', size);
  if (variant !== 'generated') params.set('variant', variant);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export const libraryApi = {

  getLibraries: (mediaServerId: number, enabled?: boolean) => {
    const params = enabled !== undefined ? `?enabled=${enabled}` : '';
    return api.get<Library[]>(`/media-servers/${mediaServerId}/libraries${params}`);
  },

  getLibrary: (mediaServerId: number, libraryId: number) =>
    api.get<Library>(`/media-servers/${mediaServerId}/libraries/${libraryId}`),

  getLibraryItems: (
    mediaServerId: number,
    libraryId: number,
    options?: {
      search?: string; status?: ItemStatusFilter; provider?: string;
      page?: number; pageSize?: number;
      sortBy?: string; sortDir?: 'asc' | 'desc';
    }
  ) => {
    const params = new URLSearchParams();
    if (options?.search) params.append('search', options.search);
    if (options?.status) params.append('status', options.status);
    if (options?.provider) params.append('provider', options.provider);
    if (options?.page !== undefined) params.append('page', options.page.toString());
    if (options?.pageSize !== undefined) params.append('page_size', options.pageSize.toString());
    if (options?.sortBy) params.append('sort_by', options.sortBy);
    if (options?.sortDir) params.append('sort_dir', options.sortDir);
    const queryString = params.toString();
    return api.get<PaginatedLibraryItems>(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/items${queryString ? `?${queryString}` : ''}`
    );
  },

  getLibraryItemCounts: (
    mediaServerId: number,
    libraryId: number,
    search?: string,
    options?: { status?: ItemStatusFilter; provider?: string }
  ) => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (options?.status) params.append('status', options.status);
    if (options?.provider) params.append('provider', options.provider);
    const queryString = params.toString();
    return api.get<LibraryItemCounts>(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/items/counts${queryString ? `?${queryString}` : ''}`
    );
  },

  getLibraryAlphaIndex: (
    mediaServerId: number, libraryId: number, status?: ItemStatusFilter, pageSize?: number,
    provider?: string
  ) => {
    const query = new URLSearchParams();
    if (status) query.append('status', status);

    if (provider) query.append('provider', provider);
    if (pageSize !== undefined) query.append('page_size', pageSize.toString());
    const params = query.toString() ? `?${query}` : '';
    return api.get<AlphaIndexEntry[]>(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/items/alpha-index${params}`
    );
  },

  getTrashItems: (
    mediaServerId: number,
    libraryId: number,
    options?: { search?: string; page?: number; pageSize?: number }
  ) => {
    const params = new URLSearchParams();
    if (options?.search) params.append('search', options.search);
    if (options?.page !== undefined) params.append('page', options.page.toString());
    if (options?.pageSize !== undefined) params.append('page_size', options.pageSize.toString());
    const queryString = params.toString();
    return api.get<PaginatedLibraryItems>(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/trash${queryString ? `?${queryString}` : ''}`
    );
  },

  restoreItem: (mediaServerId: number, libraryId: number, itemId: number) =>
    api.post<void>(`/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/restore`),

  emptyTrash: (mediaServerId: number, libraryId: number) =>
    api.post<{ purged: number }>(`/media-servers/${mediaServerId}/libraries/${libraryId}/trash/empty`),

  getItem: (mediaServerId: number, libraryId: number, itemId: number) =>
    api.get<LibraryItem>(`/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}`),

  getItemWithSeasons: (mediaServerId: number, libraryId: number, itemId: number) =>
    api.get<LibraryItemWithSeasons>(`/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/seasons`),

  getSeasonEpisodes: (mediaServerId: number, libraryId: number, itemId: number, seasonNumber: number) =>
    api.get<ItemEpisode[]>(`/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/seasons/${seasonNumber}/episodes`),

  syncAllLibraries: (mediaServerId: number) =>
    api.post<SyncTaskResponse>(`/media-servers/${mediaServerId}/libraries/sync`),

  syncLibrary: (mediaServerId: number, libraryId: number) =>
    api.post<SyncTaskResponse>(`/media-servers/${mediaServerId}/libraries/${libraryId}/sync`),

  syncAllPosters: (mediaServerId: number) =>
    api.post<SyncTaskResponse>(`/media-servers/${mediaServerId}/libraries/posters/sync`),

  syncLibraryPosters: (mediaServerId: number, libraryId: number) =>
    api.post<SyncTaskResponse>(`/media-servers/${mediaServerId}/libraries/${libraryId}/posters/sync`),

  resetAllPosters: (mediaServerId: number, includeUnprocessed = false) =>
    api.post<SyncTaskResponse>(
      `/media-servers/${mediaServerId}/libraries/posters/reset?include_unprocessed=${includeUnprocessed}`
    ),

  resetLibraryPosters: (mediaServerId: number, libraryId: number, includeUnprocessed = false) =>
    api.post<SyncTaskResponse>(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/posters/reset?include_unprocessed=${includeUnprocessed}`
    ),

  uploadAllPosters: (mediaServerId: number) =>
    api.post<SyncTaskResponse>(`/media-servers/${mediaServerId}/libraries/posters/upload`),

  uploadLibraryPosters: (mediaServerId: number, libraryId: number) =>
    api.post<SyncTaskResponse>(`/media-servers/${mediaServerId}/libraries/${libraryId}/posters/upload`),

  uploadItemPoster: (mediaServerId: number, libraryId: number, itemId: number) =>
    api.post<void>(`/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/posters/upload`),

  generateSelectedPosters: (mediaServerId: number, itemIds: number[]) =>
    api.post<SyncTaskResponse>(
      `/media-servers/${mediaServerId}/libraries/items/selection/posters/generate`,
      { item_ids: itemIds }
    ),

  uploadSelectedPosters: (mediaServerId: number, itemIds: number[]) =>
    api.post<SyncTaskResponse>(
      `/media-servers/${mediaServerId}/libraries/items/selection/posters/upload`,
      { item_ids: itemIds }
    ),

  resetSelectedPosters: (mediaServerId: number, itemIds: number[]) =>
    api.post<SyncTaskResponse>(
      `/media-servers/${mediaServerId}/libraries/items/selection/posters/reset`,
      { item_ids: itemIds }
    ),

  setItemsLock: (mediaServerId: number, itemIds: number[], locked: boolean) =>
    api.put<{ changed: number }>(
      `/media-servers/${mediaServerId}/libraries/items/selection/lock`,
      { item_ids: itemIds, locked }
    ),

  setItemLock: (mediaServerId: number, libraryId: number, itemId: number, locked: boolean) =>
    api.put<LibraryItem>(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/lock`, { locked }
    ),

  syncItem: (mediaServerId: number, libraryId: number, itemId: number) =>
    api.post<LibraryItem>(`/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/sync`),

  syncItemPosters: (mediaServerId: number, libraryId: number, itemId: number) =>
    api.post<void>(`/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/posters/sync`),

  resetItemPosters: (mediaServerId: number, libraryId: number, itemId: number) =>
    api.post<LibraryItem>(`/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/posters/reset`),

  getItemPosterUrl: (
    libraryId: number,
    itemId: number,
    version?: string | null,
    size: PosterSize = 'full',
    variant: PosterVariant = 'generated'
  ) =>
    `${API_BASE}/libraries/${libraryId}/items/${itemId}/poster${posterQuery(version, size, variant)}`,

  getSeasonPosterUrl: (
    libraryId: number,
    itemId: number,
    seasonNumber: number,
    version?: string | null,
    size: PosterSize = 'full',
    variant: PosterVariant = 'generated'
  ) =>
    `${API_BASE}/libraries/${libraryId}/items/${itemId}/seasons/${seasonNumber}/poster${posterQuery(version, size, variant)}`,

  getLibrarySettings: (mediaServerId: number, libraryId: number) =>
    api.get<LibrarySettings>(`/media-servers/${mediaServerId}/libraries/${libraryId}/settings`),

  updateLibrarySettings: (mediaServerId: number, libraryId: number, update: LibrarySettingsUpdate) =>
    api.patch<LibrarySettings>(`/media-servers/${mediaServerId}/libraries/${libraryId}/settings`, update),

  getStyleStaleness: (mediaServerId: number, libraryId: number) =>
    api.get<LibraryStyleStaleness>(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/style-staleness`
    ),

  deleteLibrary: (mediaServerId: number, libraryId: number) =>
    api.delete(`/media-servers/${mediaServerId}/libraries/${libraryId}`),
};
