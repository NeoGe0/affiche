import type { LibraryItem } from '../../types';

export interface ErrorCauseCopy {

  summary: string;

  detail: string;

  steps: string[];
}

const COPY: Record<string, ErrorCauseCopy> = {
  identifier_mismatch: {
    summary: 'Likely a mismatch on your media server — this item has no IMDb or TVDB id.',
    detail: 'A correctly matched movie or show carries an IMDb and/or TVDB id alongside the TMDB ' +
      'one. This item has neither, which most likely points to a mismatch issue.',
    steps: [
      'Open the item on your media server and check it points at the right title.',
      'Correct the match there — Fix Match in Plex, Identify in Jellyfin.',
      'Come back to Affiche, sync the library, then generate the poster again.',
    ],
  },
};

export function errorCauseCopy(item: LibraryItem): ErrorCauseCopy | undefined {
  return item.error_cause ? COPY[item.error_cause] : undefined;
}
