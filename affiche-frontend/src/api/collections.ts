import { api, API_BASE } from './client';
import type { Collection, CollectionWithMembers, PaginatedCollections, SyncTaskResponse }
  from '../types';

const base = (mediaServerId: number, libraryId: number) =>
  `/media-servers/${mediaServerId}/libraries/${libraryId}/collections`;

export const collectionsApi = {
  getCollections: (
    mediaServerId: number,
    libraryId: number,
    options?: { search?: string; page?: number; pageSize?: number; sortBy?: string }
  ) => {
    const params = new URLSearchParams();
    if (options?.search) params.append('search', options.search);
    if (options?.page !== undefined) params.append('page', options.page.toString());
    if (options?.pageSize !== undefined) params.append('page_size', options.pageSize.toString());
    if (options?.sortBy) params.append('sort_by', options.sortBy);
    const query = params.toString();
    return api.get<PaginatedCollections>(`${base(mediaServerId, libraryId)}${query ? `?${query}` : ''}`);
  },

  getCollection: (mediaServerId: number, libraryId: number, collectionId: number) =>
    api.get<CollectionWithMembers>(`${base(mediaServerId, libraryId)}/${collectionId}`),

  createCollection: (mediaServerId: number, libraryId: number, title: string, itemIds: number[]) =>
    api.post<Collection>(base(mediaServerId, libraryId), { title, item_ids: itemIds }),

  renameCollection: (mediaServerId: number, libraryId: number, collectionId: number, title: string) =>
    api.patch<Collection>(`${base(mediaServerId, libraryId)}/${collectionId}`, { title }),

  deleteCollection: (mediaServerId: number, libraryId: number, collectionId: number) =>
    api.delete(`${base(mediaServerId, libraryId)}/${collectionId}`),

  addItems: (mediaServerId: number, libraryId: number, collectionId: number, itemIds: number[]) =>
    api.post<{ changed: number }>(`${base(mediaServerId, libraryId)}/${collectionId}/items`,
      { item_ids: itemIds }),

  removeItems: (mediaServerId: number, libraryId: number, collectionId: number, itemIds: number[]) =>
    api.post<{ changed: number }>(`${base(mediaServerId, libraryId)}/${collectionId}/items/remove`,
      { item_ids: itemIds }),

  resolveIds: (mediaServerId: number, libraryId: number) =>
    api.post<SyncTaskResponse>(`${base(mediaServerId, libraryId)}/resolve`),

  setLock: (mediaServerId: number, libraryId: number, collectionId: number, locked: boolean) =>
    api.put<Collection>(`${base(mediaServerId, libraryId)}/${collectionId}/lock`, { locked }),

  getPosterUrl: (libraryId: number, collectionId: number, version?: string | null) =>
    `${API_BASE}/libraries/${libraryId}/collections/${collectionId}/poster${version ? `?v=${version}` : ''}`,
};
