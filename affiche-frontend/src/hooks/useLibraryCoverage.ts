import { useEffect, useEffectEvent, useRef, useState } from 'react';

import { dashboardApi } from '../api';
import type { ItemStats } from '../types';

interface UseLibraryCoverageOptions {
  libraryId?: number;
  enabled: boolean;

  refreshKey?: number;
}

export function useLibraryCoverage({ libraryId, enabled, refreshKey = 0 }: UseLibraryCoverageOptions) {
  const [loaded, setLoaded] = useState<{ libraryId: number; stats: ItemStats } | null>(null);
  const latest = useRef(0);

  const load = useEffectEvent(async (id: number) => {
    const request = ++latest.current;
    try {
      const summary = await dashboardApi.getSummary();
      if (request !== latest.current) return;
      const row = summary.libraries.find((library) => library.library_id === id);
      setLoaded(row ? { libraryId: id, stats: row.stats } : null);
    } catch {}
  });

  useEffect(() => {
    if (!enabled || libraryId === undefined) return;
    void load(libraryId);
  }, [enabled, libraryId, refreshKey]);

  return loaded && loaded.libraryId === libraryId ? loaded.stats : undefined;
}
