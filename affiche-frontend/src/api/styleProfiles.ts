import { api } from './client';
import type { StyleProfile } from '../types';

export interface StyleProfileCreate {
  name: string;
  overlay_options?: Record<string, unknown> | null;
  text_options?: Record<string, unknown> | null;
}

export interface StyleProfileUpdate {
  name?: string;
  overlay_options?: Record<string, unknown> | null;
  text_options?: Record<string, unknown> | null;
}

export const styleProfilesApi = {
  getProfiles: () => api.get<StyleProfile[]>('/style-profiles'),

  createProfile: (profile: StyleProfileCreate) =>
    api.post<StyleProfile>('/style-profiles', profile),

  updateProfile: (profileId: number, update: StyleProfileUpdate) =>
    api.patch<StyleProfile>(`/style-profiles/${profileId}`, update),

  deleteProfile: (profileId: number) => api.delete(`/style-profiles/${profileId}`),
};
