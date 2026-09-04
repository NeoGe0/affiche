import { useEffect, useState } from 'react';

import { errorMessage, postersApi } from '../api';
import {
  parsePreviewSubject,
  serializePreviewSubject,
  type PreviewSubject,
} from '../components/settings/previewSubject';

const STORAGE_KEY = 'affiche.stylePreviewSubject';

export function usePreviewSubject(language: string) {
  const [subject, setSubject] = useState<PreviewSubject | null>(() =>
    parsePreviewSubject(localStorage.getItem(STORAGE_KEY))
  );
  const [artworkUrl, setArtworkUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!subject) {
      setArtworkUrl(null);
      setError(null);
      return;
    }

    if (subject.tmdbId === undefined && subject.tvdbId === undefined) {
      setArtworkUrl(null);
      setError(`${subject.title} has no TMDB or TVDB id to look artwork up by`);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    const load = async () => {
      try {
        const candidates = await postersApi.getPosters({
          tmdb_id: subject.tmdbId,
          tvdb_id: subject.tvdbId,
          media_type: subject.mediaType,
          language: language || undefined,
        });
        if (cancelled) return;

        setArtworkUrl(candidates[0]?.url ?? null);
        if (candidates.length === 0) setError(`No artwork found for ${subject.title}`);
      } catch (err) {
        if (cancelled) return;
        setArtworkUrl(null);
        setError(errorMessage(err, 'Failed to load preview artwork'));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [subject, language]);

  const choose = (next: PreviewSubject) => {
    localStorage.setItem(STORAGE_KEY, serializePreviewSubject(next));
    setSubject(next);
  };

  const clear = () => {
    localStorage.removeItem(STORAGE_KEY);
    setSubject(null);
  };

  return { subject, artworkUrl, isLoading, error, choose, clear };
}
