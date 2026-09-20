import type { LibraryItem } from '../../types';

export interface StagePoster {
  libraryId: number;
  itemId: number;
  title: string;
  posterVersion?: string | null;
  reason: 'generated' | 'newest';
}

export function newestWithPoster(items: LibraryItem[]): StagePoster | null {
  const item = items.find((candidate) => candidate.processed
    && (candidate.has_poster || candidate.poster_version != null));
  if (!item) return null;
  return {
    libraryId: item.library_id,
    itemId: item.id,
    title: item.title,
    posterVersion: item.poster_version,
    reason: 'newest',
  };
}

export function isNewArrival(current: StagePoster | null, next: Omit<StagePoster, 'title'>): boolean {
  if (!current) return true;
  return current.itemId !== next.itemId
    || current.libraryId !== next.libraryId
    || current.posterVersion !== next.posterVersion;
}
