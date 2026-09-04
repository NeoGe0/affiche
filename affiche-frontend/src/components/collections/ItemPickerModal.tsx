import { useEffect, useEffectEvent, useState } from 'react';
import { Search } from 'lucide-react';

import { errorMessage, libraryApi } from '../../api';
import { useToast } from '../../context/ToastContext';
import type { LibraryItem } from '../../types';
import { Modal } from '../common';
import styles from './ItemPickerModal.module.css';

const PAGE_SIZE = 40;
const SEARCH_DEBOUNCE_MS = 300;

interface ItemPickerModalProps {
  title: string;
  confirmLabel: string;
  mediaServerId: number;
  libraryId: number;

  excludedIds?: ReadonlySet<number>;
  isBusy?: boolean;
  onConfirm: (itemIds: number[]) => void;
  onClose: () => void;
}

export function ItemPickerModal({
  title,
  confirmLabel,
  mediaServerId,
  libraryId,
  excludedIds,
  isBusy = false,
  onConfirm,
  onClose,
}: ItemPickerModalProps) {
  const toast = useToast();
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchItems = useEffectEvent(async () => {
    try {
      const page = await libraryApi.getLibraryItems(mediaServerId, libraryId, {
        search: debounced || undefined,
        pageSize: PAGE_SIZE,
      });
      setItems(page.items);
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to load items.'), { title: 'Items' });
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  });

  useEffect(() => {
    setIsLoading(true);
    void fetchItems();
  }, [debounced]);

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  return (
    <Modal
      size="wide"
      label={title}
      isBusy={isBusy}
      onClose={onClose}
      footer={
        <>
          <button className={styles.secondary} onClick={onClose} disabled={isBusy}>Cancel</button>
          <button
            className={styles.primary}
            onClick={() => onConfirm([...selected])}
            disabled={isBusy || selected.size === 0}
          >
            {confirmLabel} ({selected.size})
          </button>
        </>
      }
    >
      <div className={styles.content}>
        <h2 className={styles.heading}>{title}</h2>

        <div className={styles.searchBox}>
          <Search size={16} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search this library…"
            autoFocus
          />
        </div>

        {isLoading ? (
          <p className={styles.empty}>Loading…</p>
        ) : items.length === 0 ? (
          <p className={styles.empty}>No items match.</p>
        ) : (
          <ul className={styles.list}>
            {items.map((item) => {
              const already = excludedIds?.has(item.id) ?? false;
              return (
                <li key={item.id}>
                  <label className={`${styles.row} ${already ? styles.disabled : ''}`}>
                    <input
                      type="checkbox"
                      checked={already || selected.has(item.id)}
                      disabled={already || isBusy}
                      onChange={() => toggle(item.id)}
                    />
                    <span className={styles.rowTitle}>{item.title}</span>
                    {item.year && <span className={styles.rowYear}>{item.year}</span>}
                    {already && <span className={styles.rowNote}>already in</span>}
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Modal>
  );
}
