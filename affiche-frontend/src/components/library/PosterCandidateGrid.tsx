import { Loader2 } from 'lucide-react';

import { providerLabel } from '../../constants/providers';
import type { PosterCandidate } from '../../types';
import { candidateDetails, candidateDetailsLabel } from './posterCandidateDetails';
import styles from './PosterCandidateGrid.module.css';

interface PosterCandidateGridProps {
  posters: PosterCandidate[];

  selected: string | null;
  isLoading: boolean;
  onSelect: (posterUrl: string) => void;

  onActivate?: (posterUrl: string) => void;

  compact?: boolean;

  onFindElsewhere?: () => void;
}

export function PosterCandidateGrid({
  posters,
  selected,
  isLoading,
  onSelect,
  onActivate,
  compact = false,
  onFindElsewhere,
}: PosterCandidateGridProps) {
  return (
    <div className={styles.section}>
      {isLoading ? (
        <div className={styles.loading}>
          <Loader2 size={32} className="spin" />
        </div>
      ) : posters.length === 0 ? (
        <div className={styles.empty}>
          <p>No posters found</p>
          {onFindElsewhere && (
            <button type="button" className={styles.emptyAction} onClick={onFindElsewhere}>
              Search another title or use your own image
            </button>
          )}
        </div>
      ) : (
        <div className={`${styles.grid} ${compact ? styles.compact : ''}`}>
          {posters.map((poster, index) => {
            const { url, provider } = poster;
            const isSelected = selected === url;
            const details = candidateDetails(poster);
            const detailsLabel = candidateDetailsLabel(details);
            return (

              <button
                type="button"
                key={`${url}-${index}`}
                aria-pressed={isSelected}

                aria-label={`Poster ${index + 1} from ${providerLabel(provider)}${detailsLabel ? `, ${detailsLabel}` : ''}`}
                aria-keyshortcuts={isSelected && onActivate ? 'Enter' : undefined}
                className={`${styles.item} ${isSelected ? styles.selected : ''}`}
                onClick={() => onSelect(url)}
                onDoubleClick={onActivate && (() => onActivate(url))}

                onKeyDown={(e) => {
                  if (e.key === 'Enter' && isSelected && onActivate) {
                    e.preventDefault();
                    onActivate(url);
                  }
                }}
              >
                <span className={styles.art}>
                  <img src={url} alt="" loading="lazy" />
                  {
}
                  <span className={styles.sourceBadge} aria-hidden="true">
                    {providerLabel(provider)}
                  </span>
                  {isSelected && onActivate && (
                    <span className={styles.saveHint} aria-hidden="true">Enter to save</span>
                  )}
                </span>
                {(details.language || details.size) && (
                  <span className={styles.details} aria-hidden="true">
                    <span className={details.language === 'Textless' ? styles.textless : undefined}>
                      {details.language}
                    </span>
                    {details.size && (
                      <span className={details.isSmall ? styles.small : undefined}>
                        {details.size}
                        {details.isSmall && ' · small'}
                      </span>
                    )}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
