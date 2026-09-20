import { useEffect, useEffectEvent, useState } from 'react';

import { libraryApi } from '../api';
import { neighbourIds, neighbours } from '../components/library/selection';
import type { ItemStatusFilter, Library, LibraryItem, SortState } from '../types';

interface UseItemNeighboursOptions {
  library?: Library;
  item: LibraryItem | null;
  items: LibraryItem[];
  hasMore: boolean;
  listing: { search?: string; status?: ItemStatusFilter; provider?: string; sort: SortState };
  enabled: boolean;
}

interface Resolved {

  key: string;
  previous?: LibraryItem;
  next?: LibraryItem;
}

export function useItemNeighbours({ library, item, items, hasMore, listing, enabled }: UseItemNeighboursOptions) {
  const [resolved, setResolved] = useState<Resolved | null>(null);

  const local = enabled && item ? neighbours(items, item) : {};
  const isLoaded = !!item && items.some((i) => i.id === item.id && i.library_id === item.library_id);
  const needsListing = enabled && !!item && !!library && (!isLoaded || (!local.next && hasMore));

  const listingKey = `${listing.search ?? ''}|${listing.status ?? ''}|${listing.provider ?? ''}|${listing.sort.by}|${listing.sort.dir}`;

  const key = `${item?.library_id}|${item?.id}|${listingKey}`;

  const resolve = useEffectEvent(async () => {
    const lib = library;
    const open = item;
    if (!lib || !open) return;
    const requestKey = key;
    try {
      const ids = await libraryApi.getLibraryItemIds(lib.media_server_id, lib.id, {
        search: listing.search, status: listing.status, provider: listing.provider,
        sortBy: listing.sort.by, sortDir: listing.sort.dir,
      });
      const around = neighbourIds(ids, open.id);
      const fetchOne = async (id?: number) => {
        if (id === undefined) return undefined;
        return items.find((i) => i.id === id && i.library_id === lib.id)
          ?? await libraryApi.getItem(lib.media_server_id, lib.id, id);
      };
      const [previous, next] = await Promise.all([fetchOne(around.previous), fetchOne(around.next)]);
      setResolved({ key: requestKey, previous, next });
    } catch {}
  });

  useEffect(() => {
    if (needsListing) void resolve();
  }, [needsListing, key]);

  if (needsListing && resolved?.key === key) {
    return { previous: resolved.previous ?? local.previous, next: resolved.next ?? local.next };
  }
  return local;
}
