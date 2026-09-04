import { Loader2 } from 'lucide-react';

import { providerLabel } from '../../constants/providers';
import type { PosterCandidate } from '../../types';
import styles from './PosterCandidateGrid.module.css';

interface PosterCandidateGridProps {
  posters: PosterCandidate[];

  selected: string | null;
  isLoading: boolean;
  onSelect: (posterUrl: string) => void;
}

export function PosterCandidateGrid({
  posters,
  selected,
  isLoading,
  onSelect,
}: PosterCandidateGridProps) {
  return (
    <div className={styles.section}>
      {isLoading ? (
        <div className={styles.loading}>
          <Loader2 size={32} className="spin" />
        </div>
      ) : posters.length === 0 ? (
        <div className={styles.empty}>No posters found</div>
      ) : (
        <div className={styles.grid}>
          {posters.map(({ url, provider }, index) => (

            <button
              type="button"
              key={`${url}-${index}`}
              aria-pressed={selected === url}

              aria-label={`Poster ${index + 1} from ${providerLabel(provider)}`}
              className={`${styles.item} ${selected === url ? styles.selected : ''}`}
              onClick={() => onSelect(url)}
            >
              <img src={url} alt="" loading="lazy" />
              {
}
              <span className={styles.sourceBadge} aria-hidden="true">
                {providerLabel(provider)}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
