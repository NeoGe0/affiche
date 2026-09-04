import { useEffect, useEffectEvent, useState } from 'react';

import { errorMessage, postersApi } from '../api';
import type { PosterCandidate } from '../types';

interface UsePosterCandidatesOptions {
  mediaType: 'movie' | 'show';
  tmdbId?: number;
  tvdbId?: number;

  collectionId?: number;

  seasonNumber?: number;

  provider: string;

  language: string;
}

export function usePosterCandidates({
  mediaType,
  tmdbId,
  tvdbId,
  collectionId,
  seasonNumber,
  provider,
  language,
}: UsePosterCandidatesOptions) {
  const [posters, setPosters] = useState<PosterCandidate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [isStagingCustom, setIsStagingCustom] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canBrowse = collectionId !== undefined || tmdbId !== undefined || tvdbId !== undefined;

  const fetchGrid = async () => {
    if (!canBrowse) {
      setPosters([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const candidates =
        collectionId !== undefined
          ? await postersApi.getCollectionPosters({
              collectionId,
              provider: provider || undefined,
              language: language || undefined,
            })
          : seasonNumber !== undefined
          ? await postersApi.getSeasonPosters({
              season_number: seasonNumber,
              tmdb_id: tmdbId,
              tvdb_id: tvdbId,
              provider: provider || undefined,
              language: language || undefined,
            })
          : await postersApi.getPosters({
              tmdb_id: tmdbId,
              tvdb_id: tvdbId,
              media_type: mediaType,
              provider: provider || undefined,
              language: language || undefined,
            });
      setPosters(candidates);
    } catch (err) {
      setError(errorMessage(err, 'Failed to fetch posters'));
    } finally {
      setIsLoading(false);
    }
  };

  const refetch = useEffectEvent(() => {
    void fetchGrid();
  });

  useEffect(() => {
    refetch();
  }, [seasonNumber, provider, language, canBrowse, collectionId]);

  const search = async (name: string, year?: number) => {
    setIsSearching(true);
    setError(null);
    try {
      setPosters(
        await postersApi.searchPosters({
          name,
          year,
          media_type: mediaType,
          provider: provider || undefined,
          language: language || undefined,
        })
      );
      return true;
    } catch (err) {
      setError(errorMessage(err, 'Search failed'));
      return false;
    } finally {
      setIsSearching(false);
    }
  };

  const stageCustom = async (params: { file?: File; url?: string }) => {
    setIsStagingCustom(true);
    setError(null);
    try {
      const { token } = await postersApi.uploadCustomPoster(params);
      return `custom:${token}`;
    } catch (err) {
      setError(errorMessage(err, 'Failed to add custom poster'));
      return null;
    } finally {
      setIsStagingCustom(false);
    }
  };

  return { posters, isLoading, isSearching, isStagingCustom, error, search, stageCustom };
}
