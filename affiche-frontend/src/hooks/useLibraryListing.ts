import { useEffect, useState } from 'react';

import { parseViewMode } from '../components/library/viewMode';
import type { ItemFilter, SortState } from '../types';

const VIEW_MODE_KEY = 'affiche.libraryViewMode';

const SEARCH_DEBOUNCE_MS = 300;

const DEFAULT_SORT: SortState = { by: 'title', dir: 'asc' };

export function useLibraryListing() {
  const [searchValue, setSearchValue] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filter, setFilter] = useState<ItemFilter>('all');

  const [provider, setProvider] = useState<string | undefined>(undefined);
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const [viewMode, setViewMode] = useState(() => parseViewMode(localStorage.getItem(VIEW_MODE_KEY)));

  useEffect(() => {
    localStorage.setItem(VIEW_MODE_KEY, viewMode);
  }, [viewMode]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchValue), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchValue]);

  return {

    searchValue,
    setSearchValue,

    debouncedSearch,
    filter,
    setFilter,
    provider,
    setProvider,
    sort,
    setSort,
    viewMode,
    setViewMode,
  };
}
