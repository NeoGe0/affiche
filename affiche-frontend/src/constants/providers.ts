export const PROVIDER_LABELS: Record<string, string> = {
  tmdb: 'TMDB',
  tvdb: 'TVDB',
  fanart: 'Fanart.tv',
  mediux: 'MediUX',
  tvmaze: 'TVmaze',
  shoko: 'Shoko',
};

export const POSTER_PROVIDERS = ['tmdb', 'tvdb', 'fanart', 'mediux', 'tvmaze', 'shoko'] as const;

export type PosterProvider = (typeof POSTER_PROVIDERS)[number];

export interface PosterProviderCardMeta {
  serviceName: PosterProvider;
  description: string;

  accentColor: string;

  getKeyUrl: string;
  defaultUrl: string;
}

export const POSTER_PROVIDER_CARDS: PosterProviderCardMeta[] = [
  {
    serviceName: 'tmdb',
    description: 'The Movie Database - primary source for movie and TV posters',
    accentColor: '#01B4E4',
    getKeyUrl: 'https://www.themoviedb.org/settings/api',
    defaultUrl: 'https://api.themoviedb.org/3',
  },
  {
    serviceName: 'tvdb',
    description: 'TheTVDB - TV show artwork and metadata',
    accentColor: '#6CD491',
    getKeyUrl: 'https://thetvdb.com/dashboard/account/apikey',
    defaultUrl: 'https://api4.thetvdb.com/v4',
  },
  {
    serviceName: 'fanart',
    description: 'High-quality fan artwork for movies and TV shows',
    accentColor: '#FDD835',
    getKeyUrl: 'https://fanart.tv/get-an-api-key/',
    defaultUrl: 'https://webservice.fanart.tv/v3',
  },
  {
    serviceName: 'mediux',
    description: 'Hand-curated community poster sets (requires a MediUX API token)',
    accentColor: '#8B5CF6',
    getKeyUrl: 'https://mediux.pro',
    defaultUrl: 'https://images.mediux.io',
  },
  {
    serviceName: 'tvmaze',
    description:
      'Open TV database, no API key needed — coverage for series the other providers miss',
    accentColor: '#3C948B',

    getKeyUrl: '',
    defaultUrl: 'https://api.tvmaze.com',
  },
  {
    serviceName: 'shoko',
    description:
      'Your own Shoko Server — AniDB and hand-added anime artwork. Only covers anime already in your Shoko collection',
    accentColor: '#CC3333',

    getKeyUrl: '',
    defaultUrl: 'http://localhost:8111',
  },
];

export function providerLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? provider;
}

const PROVIDERS_WITHOUT_API_KEY = new Set<string>(['tvmaze']);

export function providerRequiresApiKey(provider: string): boolean {
  return !PROVIDERS_WITHOUT_API_KEY.has(provider);
}

export type ProviderUrlMode = 'none' | 'fixed' | 'user';

const PROVIDER_URL_MODES: Record<string, ProviderUrlMode> = {
  tvdb: 'none',
  shoko: 'user',
};

export function providerUrlMode(provider: string): ProviderUrlMode {
  return PROVIDER_URL_MODES[provider] ?? 'fixed';
}
