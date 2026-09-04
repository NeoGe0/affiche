import type { Collection, LibraryItem } from '../../types';

export interface PosterTarget {

  title: string;
  year?: number;

  mediaType: 'movie' | 'show';
  tmdbId?: number;
  tvdbId?: number;

  collectionId?: number;
}

function externalId(raw?: string): number | undefined {
  if (!raw) return undefined;
  const parsed = Number.parseInt(raw, 10);
  return Number.isNaN(parsed) ? undefined : parsed;
}

export function posterTargetFromCollection(collection: Collection,
                                           libraryType?: string): PosterTarget {
  return {
    title: collection.title,
    mediaType: libraryType === 'show' ? 'show' : 'movie',
    collectionId: collection.tmdb_collection_id ?? undefined,
  };
}

export function posterTargetFromItem(item: LibraryItem): PosterTarget {
  return {
    title: item.title,
    year: item.year,
    mediaType: item.type === 'movie' ? 'movie' : 'show',
    tmdbId: externalId(item.tmdb_id),
    tvdbId: externalId(item.tvdb_id),
  };
}
