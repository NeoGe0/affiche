import type { MediaServerType } from '../../types';
import { MEDIA_SERVER_BRAND } from '../../constants/mediaServers';

export const SERVER_CONFIG: Record<MediaServerType, {
  url: string;
  tokenLabel: string;
  tokenPlaceholder: string;
  name: string;
  color: string;
}> = {
  PLEX: {
    ...MEDIA_SERVER_BRAND.PLEX,
    url: 'http://localhost:32400',
    tokenLabel: 'API Token',
    tokenPlaceholder: 'Enter Plex token',
  },
  JELLYFIN: {
    ...MEDIA_SERVER_BRAND.JELLYFIN,
    url: 'http://localhost:8096',
    tokenLabel: 'API Key',
    tokenPlaceholder: 'Enter Jellyfin API key',
  },
};
