import { useEffect, useState } from 'react';

import { errorMessage, searchApi } from '../api';
import type { SearchHit } from '../types';

const SEARCH_DEBOUNCE_MS = 250;
const MIN_TERM_LENGTH = 2;
const RESULT_LIMIT = 25;

interface SearchResult {

  term: string;
  hits: SearchHit[];

  total: number;
  error: string | null;
}

const NONE: SearchHit[] = [];

const NOTHING: SearchResult = { term: '', hits: NONE, total: 0, error: null };

export function useGlobalSearch(term: string) {
  const [result, setResult] = useState<SearchResult>(NOTHING);
  const trimmed = term.trim();
  const isActive = trimmed.length >= MIN_TERM_LENGTH;

  useEffect(() => {
    if (!isActive) return;

    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const results = await searchApi.searchItems(trimmed, RESULT_LIMIT);
        if (!cancelled) {
          setResult({ term: trimmed, hits: results.items, total: results.total, error: null });
        }
      } catch (error) {

        if (!cancelled) {
          setResult({
            term: trimmed,
            hits: NONE,
            total: 0,
            error: errorMessage(error, 'Search failed.'),
          });
        }
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [trimmed, isActive]);

  const isSettled = isActive && result.term === trimmed;

  return {
    hits: isSettled ? result.hits : NONE,
    total: isSettled ? result.total : 0,
    error: isSettled ? result.error : null,

    isLoading: isActive && !isSettled,

    isActive,

    isTruncated: isSettled && result.total > result.hits.length,
    minTermLength: MIN_TERM_LENGTH,
  };
}
