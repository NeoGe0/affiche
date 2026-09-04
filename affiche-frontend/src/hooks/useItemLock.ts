import { useState } from 'react';

import { errorMessage, libraryApi } from '../api';
import { useToast } from '../context/ToastContext';
import type { Library, LibraryItem } from '../types';

interface UseItemLockOptions {

  allLibraries: Library[];

  setItems: React.Dispatch<React.SetStateAction<LibraryItem[]>>;

  onLockChanged?: () => void;
}

const itemKey = (item: LibraryItem) => `${item.library_id}-${item.id}`;

export function useItemLock({ allLibraries, setItems, onLockChanged }: UseItemLockOptions) {
  const toast = useToast();
  const [pending, setPending] = useState<ReadonlySet<string>>(() => new Set());

  const toggle = async (item: LibraryItem) => {
    const key = itemKey(item);
    if (pending.has(key)) return;

    const library = allLibraries.find((l) => l.id === item.library_id);
    if (!library) return;

    setPending((prev) => new Set(prev).add(key));
    try {
      const updated = await libraryApi.setItemLock(
        library.media_server_id,
        item.library_id,
        item.id,
        !item.locked
      );

      setItems((prev) =>
        prev.map((row) =>
          row.id === item.id && row.library_id === item.library_id
            ? { ...row, locked: updated.locked }
            : row
        )
      );
      onLockChanged?.();
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to change the lock on this item.'), {
        title: 'Lock failed',
      });
    } finally {
      setPending((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  return {
    toggle,
    isPending: (item: LibraryItem) => pending.has(itemKey(item)),
  };
}
