import { useEffect, useEffectEvent, useState } from 'react';
import { ArrowLeft, Layers, Lock, Pencil, Plus, Trash2, Unlock, X, Images } from 'lucide-react';

import { collectionsApi, errorMessage } from '../../api';
import { useToast } from '../../context/ToastContext';
import type { Collection, CollectionWithMembers, LibraryItem } from '../../types';
import styles from './CollectionDetail.module.css';
import { memberSummary } from './collectionSummary';

interface CollectionDetailProps {
  mediaServerId: number;
  libraryId: number;
  collectionId: number;

  refreshKey?: number;
  isBusy?: boolean;
  onBack: () => void;
  onRename: (currentTitle: string) => void;
  onDelete: (title: string) => void;
  onAddItems: (memberIds: number[]) => void;
  onRemoveItem: (item: LibraryItem) => void;
  onToggleLock: (locked: boolean) => void;
  onSelectPoster: (collection: Collection) => void;
}

export function CollectionDetail({
  mediaServerId,
  libraryId,
  collectionId,
  refreshKey = 0,
  isBusy = false,
  onBack,
  onRename,
  onDelete,
  onAddItems,
  onRemoveItem,
  onToggleLock,
  onSelectPoster,
}: CollectionDetailProps) {
  const toast = useToast();
  const [collection, setCollection] = useState<CollectionWithMembers | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCollection = useEffectEvent(async () => {
    try {
      setCollection(await collectionsApi.getCollection(mediaServerId, libraryId, collectionId));
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to load this collection.'), { title: 'Collection' });
      setCollection(null);
    } finally {
      setIsLoading(false);
    }
  });

  useEffect(() => {
    void fetchCollection();
  }, [collectionId, refreshKey]);

  if (isLoading) {
    return (
      <div className={styles.container}>
        <button className={styles.backButton} onClick={onBack}>
          <ArrowLeft size={20} /> Back to collections
        </button>
        <p className={styles.empty}>Loading…</p>
      </div>
    );
  }

  if (!collection) {
    return (
      <div className={styles.container}>
        <button className={styles.backButton} onClick={onBack}>
          <ArrowLeft size={20} /> Back to collections
        </button>
        <p className={styles.empty}>This collection could not be loaded.</p>
      </div>
    );
  }

  const members = collection.members;

  return (
    <div className={styles.container}>
      <button className={styles.backButton} onClick={onBack}>
        <ArrowLeft size={20} /> Back to collections
      </button>

      <header className={styles.header}>
        <span className={styles.icon}><Layers size={22} /></span>
        <div className={styles.headings}>
          <h1 className={styles.title}>{collection.title}</h1>
          <p className={styles.subtitle}>{memberSummary(collection)}</p>
        </div>
        <div className={styles.actions}>
          <button
            className={styles.action}
            onClick={() => onAddItems(members.map((item) => item.id))}
            disabled={isBusy}
          >
            <Plus size={16} /> Add items
          </button>
          <button
            className={styles.action}
            onClick={() => onRename(collection.title)}
            disabled={isBusy}
          >
            <Pencil size={16} /> Rename
          </button>
          <button
            className={styles.action}
            onClick={() => onSelectPoster(collection)}
            disabled={isBusy}
          >
            <Images size={16} /> Select poster
          </button>
          <button
            className={styles.action}
            onClick={() => onToggleLock(!collection.locked)}
            aria-pressed={collection.locked}
            disabled={isBusy}
          >
            {collection.locked ? <Lock size={16} /> : <Unlock size={16} />}
            {collection.locked ? 'Locked' : 'Lock'}
          </button>
          <button
            className={`${styles.action} ${styles.danger}`}
            onClick={() => onDelete(collection.title)}
            disabled={isBusy}
          >
            <Trash2 size={16} /> Delete
          </button>
        </div>
      </header>

      {collection.child_count != null && collection.child_count > members.length && (
        <p className={styles.notice}>
          The media server reports {collection.child_count} items in this collection. Affiche knows
          about {members.length} — the rest are items it has not synced, or on Jellyfin, items that
          belong to another library.
        </p>
      )}

      {members.length === 0 ? (
        <p className={styles.empty}>No items in this collection yet.</p>
      ) : (
        <ul className={styles.members}>
          {members.map((item) => (
            <li key={item.id} className={styles.member}>
              <span className={styles.memberTitle} title={item.title}>{item.title}</span>
              {item.year && <span className={styles.memberYear}>{item.year}</span>}
              <button
                className={styles.remove}
                onClick={() => onRemoveItem(item)}
                disabled={isBusy}
                aria-label={`Remove ${item.title} from ${collection.title}`}
              >
                <X size={15} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
