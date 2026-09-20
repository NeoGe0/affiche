import { useEffect, useRef, useState } from 'react';

import { errorMessage, libraryApi } from '../api';
import { useToast } from '../context/ToastContext';
import { emptySelection, pruneSelection, selectRange, toggleAll, toggleId } from '../components/library/selection';
import type { LibraryItem } from '../types';

interface UseItemSelectionOptions {

  items: LibraryItem[];

  mediaServerId?: number;

  onTaskStarted: (taskId: string) => void;

  refreshListing: (silent?: boolean) => void;

  listingKey: string;
}

export function useItemSelection({
  items,
  mediaServerId,
  onTaskStarted,
  refreshListing,
  listingKey,
}: UseItemSelectionOptions) {
  const toast = useToast();
  const [selected, setSelected] = useState<ReadonlySet<number>>(emptySelection);
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [allMatching, setAllMatching] = useState<{ key: string; ids: ReadonlySet<number> } | null>(null);
  const anchor = useRef<number | null>(null);

  useEffect(() => {
    setSelected((prev) => pruneSelection(prev, items));
  }, [items]);

  const matching = allMatching?.key === listingKey ? allMatching.ids : null;
  const current = matching ?? selected;
  const ids = [...current];

  const edit = (change: (prev: ReadonlySet<number>) => ReadonlySet<number>) => {
    const base = matching ?? selected;
    setAllMatching(null);
    setSelected(change(base));
  };

  const run = async (action: (itemIds: number[]) => Promise<void>) => {
    if (!mediaServerId || ids.length === 0) return;
    setIsBusy(true);
    try {
      await action(ids);

      setSelected(emptySelection());
      setAllMatching(null);
      setIsSelectMode(false);
    } finally {
      setIsBusy(false);
    }
  };

  const runTask = (
    request: (mediaServerId: number, itemIds: number[]) => Promise<{ task_id: string }>,
    errorTitle: string,
    errorFallback: string
  ) =>
    run(async (itemIds) => {
      try {
        const { task_id } = await request(mediaServerId!, itemIds);
        onTaskStarted(task_id);
      } catch (error) {
        toast.error(errorMessage(error, errorFallback), { title: errorTitle });
      }
    });

  const setLocked = (locked: boolean) =>
    run(async (itemIds) => {
      try {
        const { changed } = await libraryApi.setItemsLock(mediaServerId!, itemIds, locked);
        toast.success(
          `${changed} item${changed === 1 ? '' : 's'} ${locked ? 'locked' : 'unlocked'}.`,
          { title: locked ? 'Locked' : 'Unlocked' }
        );
        refreshListing(true);
      } catch (error) {
        toast.error(errorMessage(error, 'Failed to change the lock on the selection.'), {
          title: 'Lock failed',
        });
      }
    });

  return {
    selected: current,
    count: current.size,
    isAllMatching: matching !== null,
    isBusy,
    isSelectMode,
    isSelected: (id: number) => current.has(id),

    toggle: (id: number, extend = false) => {
      edit((prev) => (extend ? selectRange(prev, items, anchor.current, id) : toggleId(prev, id)));
      anchor.current = id;
      setIsSelectMode(true);
    },
    toggleAll: () => edit((prev) => toggleAll(prev, items)),
    selectAllMatching: (matchingIds: number[]) => {
      setAllMatching({ key: listingKey, ids: new Set(matchingIds) });
      setIsSelectMode(true);
    },
    toggleSelectMode: () =>
      setIsSelectMode((prev) => {

        if (prev) {
          setSelected(emptySelection());
          setAllMatching(null);
        }
        return !prev;
      }),
    clear: () => {
      setSelected(emptySelection());
      setAllMatching(null);
      setIsSelectMode(false);
    },
    generate: () =>
      runTask(libraryApi.generateSelectedPosters, 'Generation failed',
              'Failed to start generation for the selection.'),
    upload: () =>
      runTask(libraryApi.uploadSelectedPosters, 'Upload failed',
              'Failed to start the upload for the selection.'),
    reset: () =>
      runTask(libraryApi.resetSelectedPosters, 'Reset failed',
              'Failed to start the reset for the selection.'),
    lock: () => setLocked(true),
    unlock: () => setLocked(false),
  };
}
