import { useEffect, useState } from 'react';

import { errorMessage, libraryApi } from '../api';
import { useToast } from '../context/ToastContext';
import { emptySelection, pruneSelection, toggleAll, toggleId } from '../components/library/selection';
import type { LibraryItem } from '../types';

interface UseItemSelectionOptions {

  items: LibraryItem[];

  mediaServerId?: number;

  onTaskStarted: (taskId: string) => void;

  refreshListing: (silent?: boolean) => void;
}

export function useItemSelection({
  items,
  mediaServerId,
  onTaskStarted,
  refreshListing,
}: UseItemSelectionOptions) {
  const toast = useToast();
  const [selected, setSelected] = useState<ReadonlySet<number>>(emptySelection);
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    setSelected((prev) => pruneSelection(prev, items));
  }, [items]);

  const ids = [...selected];

  const run = async (action: (itemIds: number[]) => Promise<void>) => {
    if (!mediaServerId || ids.length === 0) return;
    setIsBusy(true);
    try {
      await action(ids);

      setSelected(emptySelection());
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
    selected,
    count: selected.size,
    isBusy,
    isSelectMode,
    isSelected: (id: number) => selected.has(id),
    toggle: (id: number) => {
      setSelected((prev) => toggleId(prev, id));
      setIsSelectMode(true);
    },
    toggleAll: () => setSelected((prev) => toggleAll(prev, items)),
    toggleSelectMode: () =>
      setIsSelectMode((prev) => {

        if (prev) setSelected(emptySelection());
        return !prev;
      }),
    clear: () => {
      setSelected(emptySelection());
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
