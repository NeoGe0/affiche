import { useEffect, useSyncExternalStore } from 'react';

import { errorMessage, postersApi } from '../api';
import type { PosterCandidate } from '../types';

const FRESH_FOR_MS = 10 * 60 * 1000;

type Entry =
  | { status: 'loading' }
  | { status: 'ready'; posters: PosterCandidate[]; fetchedAt: number }
  | { status: 'error'; error: string };

const cache = new Map<string, Entry>();
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((listener) => listener());

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

export function resetItemArtworkCache() {
  cache.clear();
}

interface ArtworkTarget {
  mediaType: 'movie' | 'show';
  tmdbId?: number;
  tvdbId?: number;
}

function load(key: string, { mediaType, tmdbId, tvdbId }: ArtworkTarget) {
  const entry = cache.get(key);
  if (entry?.status === 'loading') return;
  if (entry?.status === 'ready' && Date.now() - entry.fetchedAt < FRESH_FOR_MS) return;

  cache.set(key, { status: 'loading' });
  emit();
  postersApi
    .getPosters({ media_type: mediaType, tmdb_id: tmdbId, tvdb_id: tvdbId })
    .then((posters) => cache.set(key, { status: 'ready', posters, fetchedAt: Date.now() }))
    .catch((err) => cache.set(key, { status: 'error', error: errorMessage(err, 'Failed to fetch posters') }))
    .finally(emit);
}

export function useItemArtwork(target: ArtworkTarget, enabled: boolean) {
  const { mediaType, tmdbId, tvdbId } = target;
  const canBrowse = tmdbId !== undefined || tvdbId !== undefined;
  const key = `${mediaType}:${tmdbId ?? ''}:${tvdbId ?? ''}`;
  const entry = useSyncExternalStore(subscribe, () => cache.get(key));

  useEffect(() => {
    if (enabled && canBrowse) load(key, { mediaType, tmdbId, tvdbId });
  }, [enabled, canBrowse, key, mediaType, tmdbId, tvdbId]);

  if (!canBrowse) return { posters: [], isLoading: false, error: null };
  return {
    posters: entry?.status === 'ready' ? entry.posters : [],
    isLoading: entry === undefined || entry.status === 'loading',
    error: entry?.status === 'error' ? entry.error : null,
  };
}
