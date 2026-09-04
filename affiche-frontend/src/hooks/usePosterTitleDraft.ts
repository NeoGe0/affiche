import { useState } from 'react';

import { postersApi } from '../api';

interface PosterTitleDraftOptions {

  defaultTitle: string;
  mediaType: string;
  tmdbId?: number;
  tvdbId?: number;

  seasonNumber?: number;
}

export function usePosterTitleDraft({
  defaultTitle,
  mediaType,
  tmdbId,
  tvdbId,
  seasonNumber,
}: PosterTitleDraftOptions) {

  const [title, setTitle] = useState(defaultTitle);
  const [language, setLanguage] = useState('');
  const [isTranslating, setIsTranslating] = useState(false);
  const [notFound, setNotFound] = useState(false);

  const changeLanguage = async (next: string) => {
    setLanguage(next);
    setNotFound(false);

    if (!next) {
      setTitle(defaultTitle);
      return;
    }

    setIsTranslating(true);
    try {
      const { title: translated } = await postersApi.getTranslatedTitle({
        media_type: mediaType,
        language: next,
        tmdb_id: tmdbId,
        tvdb_id: tvdbId,
        season_number: seasonNumber,
      });
      if (translated) setTitle(translated);
      else setNotFound(true);
    } catch {

      setNotFound(true);
    } finally {
      setIsTranslating(false);
    }
  };

  return {
    title,

    changeTitle: (value: string) => {
      setTitle(value);
      setNotFound(false);
    },
    language,
    changeLanguage,
    isTranslating,
    notFound,
  };
}
