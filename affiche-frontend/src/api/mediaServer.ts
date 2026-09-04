import { api } from './client';
import type {
  MediaServerCreate,
  MediaServerResponse,
  MediaServerTestResult,
} from '../types';

export const mediaServerApi = {

  getAll: () => api.get<MediaServerResponse[]>('/media-servers/'),

  get: (id: number) => api.get<MediaServerResponse>(`/media-servers/${id}`),

  create: (data: MediaServerCreate) =>
    api.post<MediaServerResponse>('/media-servers/', data),

  testPlex: (url: string, token: string) =>
    api.post<MediaServerTestResult>('/media-servers/plex/test', {
      url,
      token,
    }),

  testJellyfin: (url: string, apiKey: string) =>
    api.post<MediaServerTestResult>('/media-servers/jellyfin/test', {
      url,
      api_key: apiKey,
    }),

  updateToken: (id: number, token: string) =>
    api.patch<MediaServerResponse>(`/media-servers/${id}/token`, { token }),

  delete: (id: number) => api.delete(`/media-servers/${id}`),

  setLanguageOrder: (id: number, languageOrder: string[]) =>
    api.patch<MediaServerResponse>(`/media-servers/${id}/language-order`, {
      language_order: languageOrder,
    }),

  setPosterFallback: (
    id: number,
    options: { fallback_to_server_poster: boolean; skip_style_when_not_textless: boolean }
  ) => api.patch<MediaServerResponse>(`/media-servers/${id}/poster-fallback`, options),

  setWebhook: (id: number, enabled: boolean) =>
    api.patch<MediaServerResponse>(`/media-servers/${id}/webhook`, { enabled }),

  regenerateWebhook: (id: number) =>
    api.post<MediaServerResponse>(`/media-servers/${id}/webhook/regenerate`),

  testWebhook: (id: number, dryRun = true) =>
    api.post<{ status: string; dry_run: boolean; libraries: { id: number; name: string; action: string }[] }>(
      `/media-servers/${id}/webhook/test?dry_run=${dryRun}`
    ),

  getAvailableLibraries: (id: number) =>
    api.get<import('../types').MediaServerLibrary[]>(`/media-servers/${id}/available-libraries`),

  addLibraries: (
    id: number,
    libraries: import('../types').MediaServerLibrary[],
    defaults: import('../types').NewLibraryDefaults = {},
  ) => api.post(`/media-servers/${id}/available-libraries`, { libraries, ...defaults }),
};
