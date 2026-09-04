import { useCallback, useEffect, useEffectEvent, useRef, useState } from 'react';
import { errorMessage, libraryApi } from '../api';
import { useToast } from '../context/ToastContext';
import { PAGE_SIZE } from './useLibraryItems';
import type {
  AlphaIndexEntry,
  ItemFilter,
  Library,
  LibraryItem,
  SortState,
  ViewMode,
} from '../types';

interface LoadedIndex {
  key: string;
  entries: AlphaIndexEntry[];
}

function entriesFor(loaded: LoadedIndex | null, key: string): AlphaIndexEntry[] {
  return loaded?.key === key ? loaded.entries : [];
}

interface UseAlphabetIndexOptions {
  selectedLibrary?: Library;
  isTrash: boolean;
  search: string;
  filter: ItemFilter;

  provider?: string;
  viewMode: ViewMode;
  sort: SortState;

  items: LibraryItem[];

  loadUpTo: (page: number) => Promise<void>;
}

export function useAlphabetIndex({
  selectedLibrary,
  isTrash,
  search,
  filter,
  provider,
  viewMode,
  sort,
  items,
  loadUpTo,
}: UseAlphabetIndexOptions) {
  const toast = useToast();

  const listingKey = `${selectedLibrary?.id ?? ''}|${filter}|${provider ?? ''}|${isTrash}|${search}`;
  const [loaded, setLoaded] = useState<LoadedIndex | null>(null);
  const pendingScrollLetterRef = useRef<string | null>(null);

  const isEnabled = !isTrash && !!selectedLibrary && !search
    && viewMode === 'grid' && sort.by === 'title' && sort.dir === 'asc';

  const entries = entriesFor(loaded, listingKey);

  const fetchIndex = useEffectEvent(() => {
    if (!selectedLibrary) return Promise.resolve<AlphaIndexEntry[]>([]);
    return libraryApi.getLibraryAlphaIndex(
      selectedLibrary.media_server_id,
      selectedLibrary.id,
      filter === 'all' ? undefined : filter,
      PAGE_SIZE,
      provider
    );
  });

  const hasLibrary = !!selectedLibrary;

  useEffect(() => {
    if (isTrash || !hasLibrary || search) return;

    let cancelled = false;
    const load = async () => {
      try {
        const fetched = await fetchIndex();
        if (!cancelled) setLoaded({ key: listingKey, entries: fetched });
      } catch {

        if (!cancelled) setLoaded({ key: listingKey, entries: [] });
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [isTrash, hasLibrary, search, listingKey]);

  const scrollToLetter = useCallback((letter: string) => {
    document.getElementById(`alpha-anchor-${letter}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const handleLetterClick = useCallback(async (letter: string) => {
    const entry = entriesFor(loaded, listingKey).find((e) => e.letter === letter);
    if (!entry || !selectedLibrary) return;

    if ((entry.page + 1) * PAGE_SIZE <= items.length) {
      scrollToLetter(letter);
      return;
    }

    try {
      await loadUpTo(entry.page);
      pendingScrollLetterRef.current = letter;
    } catch (error) {

      toast.error(errorMessage(error, `Could not load the items under ${letter}.`), {
        title: 'Jump to letter',
      });
    }
  }, [loaded, listingKey, items.length, selectedLibrary, loadUpTo, scrollToLetter, toast]);

  useEffect(() => {
    const letter = pendingScrollLetterRef.current;
    if (!letter) return;
    pendingScrollLetterRef.current = null;
    requestAnimationFrame(() => scrollToLetter(letter));
  }, [items, scrollToLetter]);

  return { entries, isEnabled, handleLetterClick };
}
