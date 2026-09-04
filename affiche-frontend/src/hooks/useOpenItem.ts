import { useLayoutEffect, useRef, useState } from 'react';

import { errorMessage, libraryApi } from '../api';
import { useToast } from '../context/ToastContext';
import type { ItemSeason, Library, LibraryItem } from '../types';

interface UseOpenItemOptions {

  allLibraries: Library[];

  refreshListing: (silent?: boolean) => void;

  setPageBusy: (value: boolean) => void;
  setPageMessage: (message: string | null) => void;
}

interface ItemActionSpec<T> {
  request: (mediaServerId: number, libraryId: number, itemId: number) => Promise<T>;
  onSuccess: (result: T) => void;
  errorTitle: string;

  errorFallback: string;

  setBusy?: (value: boolean) => void;

  message?: string;
}

export function useOpenItem({
  allLibraries,
  refreshListing,
  setPageBusy,
  setPageMessage,
}: UseOpenItemOptions) {
  const toast = useToast();

  const [item, setItem] = useState<LibraryItem | null>(null);

  const [season, setSeason] = useState<ItemSeason | null>(null);

  const [imageRefreshKey, setImageRefreshKey] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const library = item ? allLibraries.find((l) => l.id === item.library_id) : undefined;

  const refreshImages = () => setImageRefreshKey((key) => key + 1);

  const listScrollY = useRef(0);
  const shouldRestoreScroll = useRef(false);

  useLayoutEffect(() => {
    if (item || !shouldRestoreScroll.current) return;
    shouldRestoreScroll.current = false;
    window.scrollTo(0, listScrollY.current);
  }, [item]);

  const open = (next: LibraryItem | null) => {
    if (next && !item) listScrollY.current = window.scrollY;
    setItem(next);
    if (!next) setSeason(null);
  };

  const close = () => {
    shouldRestoreScroll.current = true;
    open(null);
  };

  const markPosterStored = () => {
    setItem((prev) =>
      prev ? { ...prev, processed: true, has_poster: true, poster_version: undefined } : prev
    );
  };

  const applyProcessedEvent = (
    libraryId: number,
    itemId: number,
    processed: boolean,
    posterVersion?: string | null
  ) => {
    setItem((prev) =>
      prev && prev.id === itemId && prev.library_id === libraryId
        ? { ...prev, processed, poster_version: posterVersion, has_poster: posterVersion != null }
        : prev
    );
    refreshImages();
  };

  const applyPosterApplied = (target: 'item' | 'season') => {
    if (target === 'item') markPosterStored();
    refreshImages();
    refreshListing();
  };

  const run = async <T,>({
    request,
    onSuccess,
    errorTitle,
    errorFallback,
    setBusy,
    message,
  }: ItemActionSpec<T>) => {
    if (!item || !library) return;

    setBusy?.(true);
    if (message) setPageMessage(message);
    try {
      onSuccess(await request(library.media_server_id, item.library_id, item.id));
    } catch (error) {
      toast.error(errorMessage(error, errorFallback), { title: errorTitle });
    } finally {
      setBusy?.(false);
      if (message) setPageMessage(null);
    }
  };

  const syncMetadata = () =>
    run({
      request: libraryApi.syncItem,
      onSuccess: (updated) => {

        setItem((prev) =>
          prev && prev.library_id === updated.library_id ? { ...prev, ...updated } : prev
        );
        refreshImages();
        refreshListing(true);
      },
      errorTitle: 'Sync failed',
      errorFallback: 'Failed to sync item metadata.',

      setBusy: setPageBusy,
      message: 'Syncing metadata…',
    });

  const generatePoster = () =>
    run({
      request: libraryApi.syncItemPosters,
      onSuccess: () => {
        markPosterStored();
        refreshImages();
        refreshListing();
      },
      errorTitle: 'Generation failed',
      errorFallback: 'Failed to generate a poster for this item.',
    });

  const resetPoster = () =>
    run({
      request: libraryApi.resetItemPosters,
      onSuccess: (updated) => {

        setItem((prev) => (prev && prev.id === updated.id ? { ...prev, ...updated } : prev));
        refreshImages();
        refreshListing();
      },
      errorTitle: 'Reset failed',
      errorFallback: 'Failed to reset this item.',
    });

  const toggleLock = () =>
    run({
      request: (mediaServerId, libraryId, itemId) =>
        libraryApi.setItemLock(mediaServerId, libraryId, itemId, !item?.locked),
      onSuccess: (updated) => {
        setItem((prev) => (prev && prev.id === updated.id ? { ...prev, locked: updated.locked } : prev));
        refreshListing(true);
      },
      errorTitle: 'Lock failed',
      errorFallback: 'Failed to change the lock on this item.',
    });

  const uploadPoster = () =>
    run({
      request: libraryApi.uploadItemPoster,
      onSuccess: () => {},
      errorTitle: 'Upload failed',
      errorFallback: 'Failed to upload poster. Please try again.',
      setBusy: setIsUploading,
    });

  return {
    item,
    open,
    close,

    library,
    season,
    openSeason: setSeason,
    imageRefreshKey,
    isUploading,
    applyProcessedEvent,
    applyPosterApplied,
    refreshImages,
    syncMetadata,
    generatePoster,
    resetPoster,
    uploadPoster,
    toggleLock,
  };
}
