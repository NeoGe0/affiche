import { useState } from 'react';

import { TEXTLESS } from '../constants/languages';
import type { PosterSort } from '../components/library/posterSort';

export interface TmdbMatch {
  tmdbId: number | null;
  seasonNumber: number | null;
}

const NO_MATCH: TmdbMatch = { tmdbId: null, seasonNumber: null };

function parsed(draft: string): number | null {
  const value = Number.parseInt(draft.trim(), 10);
  return Number.isNaN(value) ? null : value;
}

interface PosterBrowseQueryOptions {
  itemTitle: string;
  year?: number;

  seasonNumber?: number;

  tmdbMatch?: TmdbMatch;

  onSourceChanged: () => void;
}

export function usePosterBrowseQuery({
  itemTitle,
  year,
  seasonNumber,
  tmdbMatch,
  onSourceChanged,
}: PosterBrowseQueryOptions) {
  const [searchTitle, setSearchTitle] = useState(itemTitle);
  const [searchYear, setSearchYear] = useState(year ? String(year) : '');
  const [customUrl, setCustomUrl] = useState('');

  const [provider, setProvider] = useState('');

  const [sort, setSort] = useState<PosterSort>('provider');

  const [language, setLanguage] = useState(TEXTLESS);

  const [searchSeasonNumber, setSearchSeasonNumber] = useState(seasonNumber ?? 0);
  const [useShowArt, setUseShowArt] = useState(false);

  const [tmdbIdDraft, setTmdbIdDraft] = useState(
    tmdbMatch?.tmdbId != null ? String(tmdbMatch.tmdbId) : '');
  const [tmdbSeasonDraft, setTmdbSeasonDraft] = useState(
    tmdbMatch?.seasonNumber != null ? String(tmdbMatch.seasonNumber) : '');
  const [appliedTmdbMatch, setAppliedTmdbMatch] = useState<TmdbMatch>(tmdbMatch ?? NO_MATCH);

  const clearTmdbMatch = (): TmdbMatch => {
    setTmdbIdDraft('');
    setTmdbSeasonDraft('');
    setAppliedTmdbMatch(NO_MATCH);
    onSourceChanged();
    return NO_MATCH;
  };

  return {
    searchTitle,
    setSearchTitle,
    searchYear,
    setSearchYear,

    yearFilter: searchYear ? parseInt(searchYear) : undefined,
    customUrl,
    setCustomUrl,

    language,
    changeLanguage: setLanguage,
    provider,
    changeProvider: (value: string) => {
      setProvider(value);
      onSourceChanged();
    },
    sort,
    changeSort: setSort,

    searchSeasonNumber,
    changeSearchSeasonNumber: (value: number) => {
      setSearchSeasonNumber(value);
      onSourceChanged();
    },
    useShowArt,
    changeUseShowArt: (value: boolean) => {
      setUseShowArt(value);
      onSourceChanged();
    },

    tmdbIdDraft,
    setTmdbIdDraft,
    tmdbSeasonDraft,
    setTmdbSeasonDraft,
    appliedTmdbMatch,

    applyTmdbMatch: (): TmdbMatch => {

      const tmdbId = parsed(tmdbIdDraft);
      if (tmdbId === null) return clearTmdbMatch();
      const match = { tmdbId, seasonNumber: parsed(tmdbSeasonDraft) };
      setAppliedTmdbMatch(match);
      onSourceChanged();
      return match;
    },

    clearTmdbMatch,
  };
}
