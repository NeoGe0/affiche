import { useEffect, useEffectEvent, useRef, useState } from 'react';

import { dashboardApi, errorMessage, libraryApi } from '../api';
import { useToast } from '../context/ToastContext';
import type { ItemStats, Library, LibraryItem } from '../types';

export const ROW_SIZE = 20;

export interface LibraryRow {
  library: Library;
  items: LibraryItem[];

  total: number;

  stats?: ItemStats;
}

interface UseLibraryRowsOptions {
  mediaServerId?: number;

  libraries: Library[];

  enabled: boolean;

  refreshKey?: number;
}

export function useLibraryRows({
  mediaServerId, libraries, enabled, refreshKey = 0,
}: UseLibraryRowsOptions) {
  const toast = useToast();
  const [rows, setRows] = useState<LibraryRow[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const request = useRef(0);
  const libraryKey = libraries.map((l) => l.id).join(',');

  const load = useEffectEvent(async () => {
    const mine = ++request.current;
    setIsLoading(true);
    try {

      const [pages, summary] = await Promise.all([
        Promise.all(libraries.map((library) =>
          libraryApi.getLibraryItems(library.media_server_id, library.id, {
            page: 0, pageSize: ROW_SIZE, sortBy: 'added_at', sortDir: 'desc',
          }))),
        dashboardApi.getSummary().catch(() => null),
      ]);
      if (mine !== request.current) return;

      const statsByLibrary = new Map(summary?.libraries.map((row) => [row.library_id, row.stats]));
      setRows(libraries.map((library, index) => ({
        library,
        items: pages[index].items,
        total: pages[index].total,
        stats: statsByLibrary.get(library.id),
      })));
    } catch (error) {
      if (mine !== request.current) return;
      toast.error(errorMessage(error, 'Could not load the libraries of this server.'),
        { title: 'Library' });
    } finally {
      setIsLoading(false);
    }
  });

  useEffect(() => {
    if (!enabled || !mediaServerId || !libraryKey) {
      setRows([]);
      return;
    }
    load();
  }, [enabled, mediaServerId, libraryKey, refreshKey]);

  return { rows, isLoading };
}
