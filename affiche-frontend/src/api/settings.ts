import { api } from './client';
import type { ServiceConfiguration, AppSettings, AppSettingsInfo, PosterConfig } from '../types';

export interface ServiceConfigurationCreate {
  name: string;
  type: 'LIBRARY' | 'PROVIDER';
  url: string;

  token?: string;
  enabled: boolean;
}

interface TestResponse {
  status: string;
  message: string;
}

export const configApi = {
  getConfig: (key: string) => api.get<ServiceConfiguration | null>(`/config/${key}`),

  findConfigs: (type?: 'PROVIDER' | 'LIBRARY') =>
    api.get<ServiceConfiguration[]>(`/config${type ? `?type=${type}` : ''}`),

  createConfig: (config: ServiceConfigurationCreate) =>
    api.post<ServiceConfiguration>('/config/', config),

  deleteConfig: (key: string) => api.delete<void>(`/config/${key}`),
};

export const serviceApi = {
  testPlex: (serviceUrl: string, serviceToken: string) =>
    api.post<TestResponse>('/service/plex/test', {
      url: serviceUrl,
      token: serviceToken,
    }),

  testProvider: (provider: string, apiKey: string, url = '') =>
    api.post<TestResponse>(`/service/provider/${provider}/test`, {
      api_key: apiKey,
      url,
    }),
};

export const settingsApi = {

  getSettings: () => api.get<AppSettings>('/settings/'),

  updateSettings: (settings: Partial<AppSettings>) =>
    api.put<AppSettings>('/settings/', settings),

  getSettingsInfo: () => api.get<AppSettingsInfo>('/settings/info'),

  getPosterConfig: () => api.get<PosterConfig>('/settings/poster-config'),

  updatePosterConfig: (config: PosterConfig) =>
    api.put<PosterConfig>('/settings/poster-config', config),
};
