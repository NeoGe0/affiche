import type { MediaServerType } from '../types';

export const MEDIA_SERVER_BRAND: Record<
  MediaServerType,
  { name: string; color: string; path: string }
> = {
  PLEX: {
    name: 'Plex',
    color: '#EBAF00',
    path: 'M11.643 0H4.68l7.679 12L4.68 24h6.963l7.677-12z',
  },
  JELLYFIN: {
    name: 'Jellyfin',
    color: '#00A4DC',
    path: 'M12 .002C5.375.002.002 5.375.002 12c0 6.625 5.373 11.998 11.998 11.998S24 18.625 24 12C24 5.375 18.625.002 12 .002zm0 1.2c5.96 0 10.798 4.838 10.798 10.798S17.96 22.798 12 22.798 1.2 17.96 1.2 12 6.04 1.202 12 1.202zm0 2.4a8.397 8.397 0 1 0 .001 16.795A8.397 8.397 0 0 0 12 3.602zm0 1.2a7.198 7.198 0 1 1-.002 14.395A7.198 7.198 0 0 1 12 4.802z',
  },
};
