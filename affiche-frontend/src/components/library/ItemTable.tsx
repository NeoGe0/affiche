import { CheckCircle, Circle, AlertTriangle, RotateCcw, ChevronUp, ChevronDown, Lock, Unlock } from 'lucide-react';
import { libraryApi } from '../../api';
import { useInfiniteScroll, usePosterImage } from '../../hooks';
import type { LibraryItem, SortState } from '../../types';
import { failureTooltip, formatDate, formatDateTime, formatFileSize, posterSource } from './format';
import styles from './ItemTable.module.css';

interface ItemTableProps {
  items: LibraryItem[];

  onItemClick?: (item: LibraryItem) => void;
  isLoading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  isLoadingMore?: boolean;
  variant?: 'default' | 'trash';
  onRestore?: (item: LibraryItem) => void;
  sort: SortState;
  onSortChange: (sort: SortState) => void;

  onToggleSelect?: (item: LibraryItem) => void;
  onToggleSelectAll?: () => void;
  isSelected?: (item: LibraryItem) => boolean;

  selectMode?: boolean;

  onToggleLock?: (item: LibraryItem) => void;
  isLockPending?: (item: LibraryItem) => boolean;
}

const COLUMNS: { key: string; label: string; sortKey?: string; className?: string }[] = [
  { key: 'title', label: 'Title', sortKey: 'title' },
  { key: 'year', label: 'Year', sortKey: 'year', className: styles.colNarrow },
  { key: 'release', label: 'Release date', sortKey: 'release_date' },
  { key: 'resolution', label: 'Resolution', sortKey: 'resolution', className: styles.colNarrow },
  { key: 'codec', label: 'Codec', sortKey: 'codec', className: styles.colNarrow },
  { key: 'size', label: 'Size', sortKey: 'size', className: styles.colNarrow },
  { key: 'status', label: 'Status', sortKey: 'status', className: styles.colNarrow },
  { key: 'provider', label: 'Source', sortKey: 'provider', className: styles.colNarrow },
  { key: 'added', label: 'Added', sortKey: 'added_at' },
];

function PosterThumb({ item }: { item: LibraryItem }) {
  const hasPoster = item.has_poster || item.poster_version != null;
  const imageUrl = libraryApi.getItemPosterUrl(
    item.library_id,
    item.id,
    item.poster_version,
    'thumb'
  );

  const { isLoaded, isError, imgKey, imgRef, onLoad, onError } = usePosterImage(imageUrl);

  return (
    <div className={styles.thumb}>
      {(!isLoaded || isError) && (
        <span className={styles.thumbPlaceholder}>{item.title.charAt(0)}</span>
      )}
      {hasPoster && !isError && (
        <img
          key={imgKey}
          ref={imgRef}
          src={imageUrl}
          alt=""
          className={`${styles.thumbImg} ${isLoaded ? styles.thumbLoaded : ''}`}
          onLoad={onLoad}
          onError={onError}
        />
      )}
    </div>
  );
}

function StatusCell({ item }: { item: LibraryItem }) {
  if (item.error_message) {
    return (
      <span className={`${styles.statusPill} ${styles.failed}`} title={failureTooltip(item)}>
        <AlertTriangle size={14} /> Failed
      </span>
    );
  }
  if (item.processed) {
    return <span className={`${styles.statusPill} ${styles.processed}`}><CheckCircle size={14} /> Processed</span>;
  }
  return <span className={`${styles.statusPill} ${styles.pending}`}><Circle size={14} /> Pending</span>;
}

export function ItemTable({
  items,
  onItemClick,
  isLoading,
  hasMore = false,
  onLoadMore,
  isLoadingMore = false,
  variant = 'default',
  onRestore,
  sort,
  onSortChange,
  onToggleSelect,
  onToggleSelectAll,
  isSelected,
  selectMode = false,
  onToggleLock,
  isLockPending,
}: ItemTableProps) {
  const isTrash = variant === 'trash';
  const loadMoreRef = useInfiniteScroll({ hasMore, isLoadingMore, onLoadMore });

  const rowClick = selectMode && onToggleSelect ? onToggleSelect : onItemClick;

  const handleSort = (sortKey?: string) => {
    if (!sortKey) return;
    if (sort.by === sortKey) {
      onSortChange({ by: sortKey, dir: sort.dir === 'asc' ? 'desc' : 'asc' });
    } else {
      onSortChange({ by: sortKey, dir: 'asc' });
    }
  };

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <span>Loading items...</span>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        {isTrash ? (
          <>
            <p>Trash is empty</p>
            <p className="text-muted">Items removed from your media server will appear here</p>
          </>
        ) : (
          <>
            <p>No items found</p>
            <p className="text-muted">Sync your library to see items here</p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={styles.tableContainer}>
      <table className={styles.table}>
        <thead>
          <tr>
            {onToggleSelect && (
              <th className={styles.colSelect}>
                <input
                  type="checkbox"
                  checked={items.length > 0 && items.every((item) => isSelected?.(item))}
                  onChange={onToggleSelectAll}
                  aria-label="Select all listed items"
                />
              </th>
            )}
            <th className={styles.colThumb} aria-hidden="true" />
            {COLUMNS.map((col) => {
              const active = col.sortKey && sort.by === col.sortKey;
              const chevron = active
                ? (sort.dir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)
                : null;
              return (
                <th
                  key={col.key}
                  className={`${col.className || ''} ${col.sortKey ? styles.sortable : ''} ${active ? styles.active : ''}`}

                  aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending')
                    : col.sortKey ? 'none' : undefined}
                >
                  {col.sortKey ? (

                    <button
                      type="button"
                      className={styles.headerButton}
                      onClick={() => handleSort(col.sortKey)}
                    >
                      <span className={styles.headerLabel}>{col.label}{chevron}</span>
                    </button>
                  ) : (
                    <span className={styles.headerLabel}>{col.label}</span>
                  )}
                </th>
              );
            })}
            {onToggleLock && (
              <th className={styles.colLock}>
                <span className={styles.headerLabel}>
                  <Lock size={14} aria-label="Locked" />
                </span>
              </th>
            )}
            {isTrash && <th className={styles.colNarrow} aria-hidden="true" />}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={`${item.library_id}-${item.id}`}
              className={`${styles.row} ${isTrash ? styles.trashRow : ''} ${isSelected?.(item) ? styles.selectedRow : ''}`}
              onClick={rowClick ? () => rowClick(item) : undefined}
            >
              {onToggleSelect && (
                <td className={styles.colSelect} onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={!!isSelected?.(item)}
                    onChange={() => onToggleSelect(item)}
                    aria-label={`Select ${item.title}`}
                  />
                </td>
              )}
              <td className={styles.colThumb}><PosterThumb item={item} /></td>
              <td className={styles.titleCell} title={item.title}>
                {rowClick ? (

                  <button
                    type="button"
                    className={styles.titleButton}
                    onClick={(e) => { e.stopPropagation(); rowClick(item); }}
                  >
                    {item.title}
                  </button>
                ) : (
                  item.title
                )}
              </td>
              <td className={styles.colNarrow}>{item.year ?? '—'}</td>
              <td>{formatDate(item.release_date)}</td>
              <td className={`${styles.colNarrow} ${styles.quality}`}>{item.media_resolution || '—'}</td>
              <td className={`${styles.colNarrow} ${styles.quality}`}>{item.video_codec ? item.video_codec.toUpperCase() : '—'}</td>
              <td className={`${styles.colNarrow} ${styles.quality}`}>{formatFileSize(item.media_size_bytes)}</td>
              <td className={styles.colNarrow}><StatusCell item={item} /></td>
              <td className={styles.colNarrow}>{posterSource(item.poster_provider)}</td>
              <td>{formatDateTime(item.added_at)}</td>
              {onToggleLock && (
                <td className={styles.colLock} onClick={(e) => e.stopPropagation()}>
                  <button
                    className={`${styles.lockButton} ${item.locked ? styles.lockButtonOn : ''}`}
                    onClick={() => onToggleLock(item)}
                    disabled={isLockPending?.(item)}
                    aria-pressed={item.locked}
                    aria-label={`${item.locked ? 'Unlock' : 'Lock'} the poster for ${item.title}`}
                    title={
                      item.locked
                        ? 'Locked — poster generation skips this item. Click to unlock.'
                        : 'Lock this poster against regeneration'
                    }
                  >
                    {item.locked ? <Lock size={14} /> : <Unlock size={14} />}
                  </button>
                </td>
              )}
              {isTrash && (
                <td className={styles.colNarrow}>
                  {onRestore && (
                    <button
                      className={styles.restoreButton}
                      onClick={(e) => { e.stopPropagation(); onRestore(item); }}
                      title="Restore item"
                    >
                      <RotateCcw size={14} /> Restore
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {}
      <div ref={loadMoreRef} className={styles.loadMoreTrigger}>
        {isLoadingMore && (
          <div className={styles.loadingMore}>
            <div className={styles.spinner} />
            <span>Loading more...</span>
          </div>
        )}
      </div>
    </div>
  );
}
