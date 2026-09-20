import { useId } from 'react';
import { RotateCcw, Lock, Unlock } from 'lucide-react';
import { libraryApi } from '../../api';
import { usePosterImage } from '../../hooks';
import type { LibraryItem } from '../../types';
import { failureTooltip } from './format';
import { POSTER_STATE_LABEL, posterState } from './posterState';
import styles from './ItemCard.module.css';

interface ItemCardProps {
  item: LibraryItem;

  onClick?: () => void;
  variant?: 'default' | 'trash';
  onRestore?: () => void;

  onToggleSelect?: (extend: boolean) => void;
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
  const failure = isTrash ? undefined : failureTooltip(item);
  const failureId = useId();

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
      className={`${styles.card} ${isTrash ? styles.trash : ''} ${isSelected ? styles.selected : ''} ${inSelectMode ? styles.selectMode : ''} ${activate ? styles.openable : ''}`}

      onClick={activate ? (e) => activate(e.shiftKey) : undefined}
      id={anchorLetter ? `alpha-anchor-${anchorLetter}` : undefined}
      style={anchorLetter ? { scrollMarginTop: 'calc(var(--header-height) + 16px)' } : undefined}
    >
      {
}
      {activate && (
        <button
          type="button"
          className={styles.open}
          onClick={(e) => { e.stopPropagation(); activate(e.shiftKey); }}
          aria-pressed={inSelectMode ? isSelected : undefined}
          aria-label={inSelectMode ? item.title : `Open ${item.title}`}
          aria-describedby={failure ? failureId : undefined}
        />
      )}
      <div className={styles.poster}>
        {onToggleSelect && (

          <label
            className={`${styles.selectBox} ${isSelected ? styles.selectBoxOn : ''}`}
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="checkbox"
              checked={isSelected}
              onChange={(e) => onToggleSelect((e.nativeEvent as MouseEvent).shiftKey === true)}
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

        {isTrash && (
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
        )}
      </div>
      <div className={styles.info}>
        <h3 className={styles.title} title={item.title}>
          {item.title}
        </h3>
        <div className={styles.meta}>
          {!isTrash && (
            <span className={`${styles.state} ${styles[posterState(item)]}`} title={failure}>
              <span className={styles.stateDot} aria-hidden="true" />
              {POSTER_STATE_LABEL[posterState(item)]}
            </span>
          )}
          {failure && (
            <span id={failureId} className="visually-hidden">{failure}</span>
          )}
          {item.year && <span className={styles.year}>{item.year}</span>}
        </div>
      </div>
    </div>
  );
}
