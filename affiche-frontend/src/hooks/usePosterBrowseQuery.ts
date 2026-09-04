import { useState } from 'react';

import { TEXTLESS } from '../constants/languages';
import type { PosterSort } from '../components/library/posterSort';

interface PosterBrowseQueryOptions {
  itemTitle: string;
  year?: number;

  seasonNumber?: number;

  onSourceChanged: () => void;
}

export function usePosterBrowseQuery({
  itemTitle,
  year,
  seasonNumber,
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
  };
}
