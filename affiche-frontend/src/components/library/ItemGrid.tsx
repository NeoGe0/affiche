import { useInfiniteScroll } from '../../hooks';
import { ItemCard } from './ItemCard';
import { bucketLetter } from './alphaBucket';
import type { LibraryItem } from '../../types';
import styles from './ItemGrid.module.css';

interface ItemGridProps {
  items: LibraryItem[];

  onItemClick?: (item: LibraryItem) => void;
  isLoading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  isLoadingMore?: boolean;
  variant?: 'default' | 'trash';
  onRestore?: (item: LibraryItem) => void;

  showAnchors?: boolean;

  onToggleSelect?: (item: LibraryItem) => void;
  isSelected?: (item: LibraryItem) => boolean;

  selectMode?: boolean;

  onToggleLock?: (item: LibraryItem) => void;
  isLockPending?: (item: LibraryItem) => boolean;
}

export function ItemGrid({
  items,
  onItemClick,
  isLoading,
  hasMore = false,
  onLoadMore,
  isLoadingMore = false,
  variant = 'default',
  onRestore,
  showAnchors = false,
  onToggleSelect,
  isSelected,
  selectMode = false,
  onToggleLock,
  isLockPending,
}: ItemGridProps) {
  const loadMoreRef = useInfiniteScroll({ hasMore, isLoadingMore, onLoadMore });

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
        {variant === 'trash' ? (
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

  const seenLetters = new Set<string>();

  return (
    <div className={styles.gridContainer}>
      <div className={`${styles.grid} ${showAnchors ? styles.withRail : ''}`}>
        {items.map((item) => {
          let anchorLetter: string | undefined;
          if (showAnchors) {
            const letter = bucketLetter(item.title);
            if (!seenLetters.has(letter)) {
              seenLetters.add(letter);
              anchorLetter = letter;
            }
          }
          return (
            <ItemCard
              key={`${item.library_id}-${item.id}`}
              item={item}
              onClick={onItemClick ? () => onItemClick(item) : undefined}
              variant={variant}
              onRestore={onRestore ? () => onRestore(item) : undefined}
              onToggleSelect={onToggleSelect ? () => onToggleSelect(item) : undefined}
              isSelected={isSelected?.(item)}
              selectMode={selectMode}
              onToggleLock={onToggleLock ? () => onToggleLock(item) : undefined}
              isLockPending={isLockPending?.(item)}
              anchorLetter={anchorLetter}
            />
          );
        })}
      </div>

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
