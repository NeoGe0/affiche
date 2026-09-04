import { Layers, Lock } from 'lucide-react';

import { collectionsApi } from '../../api';
import { usePosterImage } from '../../hooks';
import type { Collection } from '../../types';
import { activationProps } from '../common';
import styles from './CollectionCard.module.css';
import { memberSummary } from './collectionSummary';

interface CollectionCardProps {
  collection: Collection;
  onClick?: () => void;
}

export function CollectionCard({ collection, onClick }: CollectionCardProps) {

  const hasPoster = collection.has_poster || collection.poster_version != null;
  const imageUrl = collectionsApi.getPosterUrl(collection.library_id, collection.id,
                                               collection.poster_version);

  const { isLoaded, isError, imgKey, imgRef, onLoad, onError } = usePosterImage(imageUrl);

  return (
    <div className={styles.card} {...activationProps(onClick)}>
      <div className={styles.poster}>
        {(!isLoaded || isError) && (
          <div className={styles.placeholder}>
            <Layers size={28} />
          </div>
        )}

        {hasPoster && !isError && (
          <img
            key={imgKey}
            ref={imgRef}
            src={imageUrl}
            alt={collection.title}
            className={`${styles.image} ${isLoaded ? styles.loaded : ''}`}
            onLoad={onLoad}
            onError={onError}
          />
        )}

        {collection.locked && (
          <span className={styles.lockBadge} title="Locked — poster generation skips this collection">
            <Lock size={12} />
          </span>
        )}
      </div>
      <div className={styles.info}>
        <h3 className={styles.title} title={collection.title}>{collection.title}</h3>
        <span className={styles.count}>{memberSummary(collection)}</span>
      </div>
    </div>
  );
}
