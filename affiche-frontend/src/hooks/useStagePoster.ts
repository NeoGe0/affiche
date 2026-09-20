import { useEffect, useEffectEvent, useRef, useState } from 'react';

import { libraryApi } from '../api';
import { isNewArrival, newestWithPoster, type StagePoster } from '../components/library/stagePoster';
import type { Library, LibraryItem } from '../types';

const DWELL_MS = 4000;
const NEWEST_PAGE = 12;

interface UseStagePosterOptions {

  library?: Library;

  items: LibraryItem[];
  enabled: boolean;
}

export function useStagePoster({ library, items, enabled }: UseStagePosterOptions) {
  const [staged, setStaged] = useState<StagePoster | null>(null);
  const offer = useRef<Omit<StagePoster, 'title'> | null>(null);

  const libraryId = library?.id;
  const mediaServerId = library?.media_server_id;

  useEffect(() => {
    if (!enabled || libraryId === undefined || mediaServerId === undefined) return;
    let cancelled = false;
    const load = async () => {
      try {
        const page = await libraryApi.getLibraryItems(mediaServerId, libraryId, {

          pageSize: NEWEST_PAGE, sortBy: 'poster_generated_at', sortDir: 'desc',
        });
        if (cancelled) return;

        setStaged((prev) => (prev?.reason === 'generated' && prev.libraryId === libraryId
          ? prev
          : newestWithPoster(page.items)));
      } catch {}
    };
    void load();
    return () => { cancelled = true; };
  }, [enabled, libraryId, mediaServerId]);

  const takeOffer = useEffectEvent(async () => {
    const next = offer.current;
    offer.current = null;
    if (!next || mediaServerId === undefined || !isNewArrival(staged, next)) return;

    const listed = items.find((item) => item.id === next.itemId && item.library_id === next.libraryId);
    let title = listed?.title;
    if (!title) {
      try {
        title = (await libraryApi.getItem(mediaServerId, next.libraryId, next.itemId)).title;
      } catch {
        return;
      }
    }
    setStaged({ ...next, title });
  });

  useEffect(() => {
    if (!enabled) return;
    const timer = window.setInterval(() => { void takeOffer(); }, DWELL_MS);
    return () => window.clearInterval(timer);
  }, [enabled]);

  return {

    poster: staged?.libraryId === libraryId ? staged : null,
    offerGenerated: (eventLibraryId: number, itemId: number, posterVersion?: string | null) => {
      if (eventLibraryId !== libraryId || posterVersion == null) return;
      offer.current = { libraryId: eventLibraryId, itemId, posterVersion, reason: 'generated' };
    },
  };
}
