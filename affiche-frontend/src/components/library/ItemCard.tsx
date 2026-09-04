import { CheckCircle, Circle, RotateCcw, AlertTriangle, Lock, Unlock } from 'lucide-react';
import { libraryApi } from '../../api';
import { usePosterImage } from '../../hooks';
import type { LibraryItem } from '../../types';
import { activationProps } from '../common';
import { failureTooltip } from './format';
import styles from './ItemCard.module.css';

interface ItemCardProps {
  item: LibraryItem;

  onClick?: () => void;
  variant?: 'default' | 'trash';
  onRestore?: () => void;

  onToggleSelect?: () => void;
  isSelected?: boolean;

  selectMode?: boolean;

  onToggleLock?: () => void;

  isLockPending?: boolean;

  anchorLetter?: string;
}

export function ItemCard({
  item, onClick, variant = 'default', onRestore, onToggleSelect, isSelected = false,
  selectMode = false, onToggleLock, isLockPending = false, anchorLetter,
}: ItemCardProps) {
  const isTrash = variant === 'trash';

  const inSelectMode = selectMode && !!onToggleSelect;
  const activate = inSelectMode ? onToggleSelect : onClick;

  const hasPoster = item.has_poster || item.poster_version != null;

  const imageUrl = libraryApi.getItemPosterUrl(
    item.library_id,
    item.id,
    item.poster_version,
    'thumb'
  );

  const { isLoaded, isError, imgKey, imgRef, onLoad, onError } = usePosterImage(imageUrl);

  return (
    <div
      className={`${styles.card} ${isTrash ? styles.trash : ''} ${isSelected ? styles.selected : ''} ${inSelectMode ? styles.selectMode : ''}`}
      {...activationProps(activate)}
      aria-pressed={inSelectMode ? isSelected : undefined}
      id={anchorLetter ? `alpha-anchor-${anchorLetter}` : undefined}
      style={anchorLetter ? { scrollMarginTop: 'calc(var(--header-height) + 16px)' } : undefined}
    >
      <div className={styles.poster}>
        {onToggleSelect && (

          <label
            className={`${styles.selectBox} ${isSelected ? styles.selectBoxOn : ''}`}
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="checkbox"
              checked={isSelected}
              onChange={onToggleSelect}
              aria-label={`Select ${item.title}`}
            />
          </label>
        )}

        {}
        {(!isLoaded || isError) && (
          <div className={styles.placeholder}>
            <span>{item.title.charAt(0)}</span>
          </div>
        )}

        {
}
        {hasPoster && !isError && (
          <img
            key={imgKey}
            ref={imgRef}
            src={imageUrl}
            alt={item.title}
            className={`${styles.image} ${isLoaded ? styles.loaded : ''}`}
            onLoad={onLoad}
            onError={onError}
          />
        )}

        {!isTrash && item.error_message && (
          <div className={styles.badges}>
            <span className={`${styles.badge} ${styles.failedBadge}`} title={failureTooltip(item)}>
              <AlertTriangle size={12} />
              Failed
            </span>
          </div>
        )}

        {

}
        {!isTrash && onToggleLock && !inSelectMode && (
          <button
            className={`${styles.lockButton} ${item.locked ? styles.lockButtonOn : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggleLock();
            }}
            disabled={isLockPending}
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
        )}

        {isTrash ? (
          onRestore && (
            <button
              className={styles.restoreButton}
              onClick={(e) => {
                e.stopPropagation();
                onRestore();
              }}
              title="Restore item"
            >
              <RotateCcw size={16} />
              <span>Restore</span>
            </button>
          )
        ) : (
          <div className={styles.status}>
            {item.error_message ? (
              <AlertTriangle size={20} className={styles.failed} />
            ) : item.processed ? (
              <CheckCircle size={20} className={styles.processed} />
            ) : (
              <Circle size={20} className={styles.pending} />
            )}
          </div>
        )}
      </div>
      <div className={styles.info}>
        <h3 className={styles.title} title={item.title}>
          {item.title}
        </h3>
        {item.year && <span className={styles.year}>{item.year}</span>}
      </div>
    </div>
  );
}
