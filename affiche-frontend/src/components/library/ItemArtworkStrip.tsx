import { Search } from 'lucide-react';

import { providerLabel } from '../../constants/providers';
import { useInView, useItemArtwork } from '../../hooks';
import type { PosterTarget } from './posterTarget';
import styles from './ItemArtworkStrip.module.css';

const SHOWN = 7;

interface ItemArtworkStripProps {
  target: PosterTarget;

  onPick: (posterUrl?: string) => void;
}

export function ItemArtworkStrip({ target, onPick }: ItemArtworkStripProps) {
  const [sectionRef, isNear] = useInView<HTMLElement>();
  const { posters, isLoading, error } = useItemArtwork(target, isNear);

  const shown = posters.slice(0, SHOWN);

  return (
    <section ref={sectionRef} className={styles.section} aria-labelledby="item-artwork-heading">
      <h2 id="item-artwork-heading" className={styles.heading}>Other artwork</h2>
      {error && <p className={styles.note}>{error}</p>}
      {!isLoading && !error && shown.length === 0 && (
        <p className={styles.note}>Your providers have no artwork for this title.</p>
      )}
      <div className={styles.strip}>
        {isLoading
          ? Array.from({ length: 5 }, (_, i) => <div key={i} className={styles.skeleton} />)
          : shown.map(({ url, provider }, index) => (
              <button
                type="button"
                key={`${url}-${index}`}
                className={styles.tile}
                onClick={() => onPick(url)}
                aria-label={`Use poster ${index + 1} from ${providerLabel(provider)}`}
              >
                <span className={styles.art}>
                  <img src={url} alt="" loading="lazy" />
                </span>
                <span className={styles.caption}>{providerLabel(provider)}</span>
              </button>
            ))}
        <button type="button" className={styles.tile} onClick={() => onPick()}>
          <span className={`${styles.art} ${styles.more}`}>
            <Search size={18} />
            Search, paste a URL or pick a file
          </span>
          <span className={styles.caption}>More artwork</span>
        </button>
      </div>
    </section>
  );
}
