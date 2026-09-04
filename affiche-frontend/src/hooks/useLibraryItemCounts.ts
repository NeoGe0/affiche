import { useEffect, useEffectEvent, useState } from 'react';

import { libraryApi } from '../api';
import type { ItemFilter, Library, LibraryItemCounts } from '../types';

interface UseLibraryItemCountsOptions {

  libraries: Library[];

  selectedLibrary?: Library;

  isTrash: boolean;
  search: string;

  filter: ItemFilter;

  provider?: string;

  enabled?: boolean;
}

interface LoadedCounts {
  key: string;
  counts: LibraryItemCounts;
}

const ZERO: LibraryItemCounts = { total: 0, unprocessed: 0, errors: 0, locked: 0, providers: {} };

function sumProviders(all: LibraryItemCounts[]): Record<string, number> {
  const merged: Record<string, number> = {};
  for (const counts of all) {
    for (const [provider, count] of Object.entries(counts.providers ?? {})) {
      merged[provider] = (merged[provider] ?? 0) + count;
    }
  }
  return merged;
}

function sum(all: LibraryItemCounts[]): LibraryItemCounts {
  return all.reduce(
    (acc, c) => ({
      total: acc.total + c.total,
      unprocessed: acc.unprocessed + c.unprocessed,
      errors: acc.errors + c.errors,
      locked: acc.locked + c.locked,
      providers: acc.providers,
    }),
    { ...ZERO, providers: sumProviders(all) }
  );
}

export function useLibraryItemCounts({
  libraries,
  selectedLibrary,
  isTrash,
  search,
  filter,
  provider,
  enabled = true,
}: UseLibraryItemCountsOptions) {
  const targets = selectedLibrary ? [selectedLibrary] : libraries;
  const listingKey = `${selectedLibrary?.id ?? 'all'}|${isTrash}|${search}|${filter}|${provider ?? ''}`
    + `|${targets.map((l) => l.id).join(',')}`;

  const [loaded, setLoaded] = useState<LoadedCounts | null>(null);

  const [refreshToken, setRefreshToken] = useState(0);

  const counts = loaded?.key === listingKey ? loaded.counts : undefined;

  const fetchCounts = useEffectEvent(() => {
    const scope = selectedLibrary ? [selectedLibrary] : libraries;
    return Promise.allSettled(
      scope.map((lib) =>
        libraryApi.getLibraryItemCounts(lib.media_server_id, lib.id, search || undefined, {
          status: filter === 'all' ? undefined : filter,
          provider,
        })
      )
    );
  });

  const hasTargets = targets.length > 0;

  useEffect(() => {
    if (!enabled || isTrash || !hasTargets) return;

    let cancelled = false;
    const load = async () => {
      const results = await fetchCounts();
      if (cancelled) return;
      const fulfilled = results
        .filter((r) => r.status === 'fulfilled')
        .map((r) => r.value);
      if (fulfilled.length > 0) setLoaded({ key: listingKey, counts: sum(fulfilled) });
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [enabled, listingKey, isTrash, hasTargets, refreshToken]);

  return {
    counts,

    reload: () => setRefreshToken((n) => n + 1),
  };
}
