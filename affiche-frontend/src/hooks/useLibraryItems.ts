import { useCallback, useEffect, useEffectEvent, useRef, useState } from 'react';
import { errorMessage, libraryApi } from '../api';
import { useToast } from '../context/ToastContext';
import type { ItemFilter, Library, LibraryItem, SortState } from '../types';

export const PAGE_SIZE = 50;

interface UseLibraryItemsOptions {
  mediaServerId?: number;

  libraries: Library[];

  selectedLibrary?: Library;
  isTrash: boolean;
  search: string;
  filter: ItemFilter;

  provider?: string;
  sort: SortState;

  enabled?: boolean;
}

export function useLibraryItems({
  mediaServerId,
  libraries,
  selectedLibrary,
  isTrash,
  search,
  filter,
  provider,
  sort,
  enabled = true,
}: UseLibraryItemsOptions) {
  const toast = useToast();

  const [items, setItems] = useState<LibraryItem[]>([]);
  const [total, setTotal] = useState(0);

  const loadedPages = useRef(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const listing = useRef(0);

  const fetchLibraryPage = useCallback(
    (lib: Library, pageIndex: number, pageSize: number = PAGE_SIZE) => {
      if (isTrash) {
        return libraryApi.getTrashItems(lib.media_server_id, lib.id, {
          search: search || undefined,
          page: pageIndex,
          pageSize,
        });
      }
      return libraryApi.getLibraryItems(lib.media_server_id, lib.id, {
        search: search || undefined,
        status: filter === 'all' ? undefined : filter,
        provider,
        page: pageIndex,
        pageSize,
        sortBy: sort.by,
        sortDir: sort.dir,
      });
    },
    [isTrash, search, filter, provider, sort]
  );

  const fetchItems = useCallback(async (silent = false) => {
    if (!mediaServerId) return;

    if (!silent) setIsLoading(true);
    const requested = listing.current;
    const pages = Math.max(loadedPages.current, 1);
    const pageSize = pages * PAGE_SIZE;

    try {
      if (selectedLibrary) {
        const data = await fetchLibraryPage(selectedLibrary, 0, pageSize);
        if (requested !== listing.current) return;

        setItems(data.items);
        setTotal(data.total);
        loadedPages.current = pages;
      } else {
        const allData = await Promise.all(
          libraries.map((lib) => fetchLibraryPage(lib, 0, pageSize))
        );
        if (requested !== listing.current) return;

        setItems(allData.flatMap((d) => d.items));
        setTotal(allData.reduce((sum, d) => sum + d.total, 0));
        loadedPages.current = pages;
      }
    } catch (error) {
      if (requested !== listing.current) return;

      toast.error(errorMessage(error, 'Could not load the items in this library.'), {
        title: 'Library',
      });
    } finally {

      setIsLoading(false);
    }
  }, [mediaServerId, selectedLibrary, libraries, fetchLibraryPage, toast]);

  const loadMoreItems = useCallback(async () => {
    if (isLoadingMore || !mediaServerId) return;

    setIsLoadingMore(true);
    const requested = listing.current;

    try {
      const next = loadedPages.current;
      if (selectedLibrary) {
        const data = await fetchLibraryPage(selectedLibrary, next);
        if (requested !== listing.current) return;

        setItems((prev) => [...prev, ...data.items]);
        loadedPages.current = next + 1;
      } else {
        const allData = await Promise.all(libraries.map((lib) => fetchLibraryPage(lib, next)));
        if (requested !== listing.current) return;

        setItems((prev) => [...prev, ...allData.flatMap((d) => d.items)]);
        loadedPages.current = next + 1;
      }
    } catch (error) {
      if (requested !== listing.current) return;
      toast.error(errorMessage(error, 'Could not load more items.'), { title: 'Library' });
    } finally {
      setIsLoadingMore(false);
    }
  }, [mediaServerId, selectedLibrary, libraries, fetchLibraryPage, isLoadingMore, toast]);

  const loadUpTo = useCallback(async (targetPage: number) => {
    if (!selectedLibrary) return;
    const requested = listing.current;
    const data = await fetchLibraryPage(selectedLibrary, 0, (targetPage + 1) * PAGE_SIZE);
    if (requested !== listing.current) return;
    setItems(data.items);
    setTotal(data.total);
    loadedPages.current = targetPage + 1;
  }, [selectedLibrary, fetchLibraryPage]);

  useEffect(() => {
    listing.current += 1;
    setItems([]);
    loadedPages.current = 0;
    setTotal(0);
  }, [search, selectedLibrary?.id, filter, provider, mediaServerId, isTrash, sort]);

  const libraryKey = libraries.map((l) => l.id).join(',');

  const loadFirstPage = useEffectEvent(() => {
    fetchItems();
  });

  useEffect(() => {
    if (!enabled || !mediaServerId || !libraryKey) return;
    loadFirstPage();
  }, [enabled, mediaServerId, libraryKey, selectedLibrary?.id, isTrash, search, filter, provider, sort]);

  const hasMore = items.length < total;

  const handleLoadMore = useCallback(() => {
    if (!isLoadingMore && hasMore) {
      loadMoreItems();
    }
  }, [isLoadingMore, hasMore, loadMoreItems]);

  return {
    items,
    setItems,
    total,
    setTotal,
    isLoading,
    isLoadingMore,
    hasMore,
    fetchItems,
    handleLoadMore,
    loadUpTo,
  };
}
