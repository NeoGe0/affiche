import { useState, type CSSProperties, type ReactNode } from 'react';
import { usePosterImage } from '../../hooks';
import styles from './PosterCompareSlider.module.css';

interface PosterCompareSliderProps {

  beforeUrl: string;

  afterUrl: string;

  alt: string;

  placeholder?: ReactNode;
}

export function PosterCompareSlider({ beforeUrl, afterUrl, alt, placeholder }: PosterCompareSliderProps) {
  const [position, setPosition] = useState(50);

  const {
    isLoaded: afterLoaded, isError: afterError, imgKey: afterKey, imgRef: afterRef,
    onLoad: onAfterLoad, onError: onAfterError,
  } = usePosterImage(afterUrl);
  const {
    isLoaded: beforeLoaded, isError: beforeError, imgKey: beforeKey, imgRef: beforeRef,
    onLoad: onBeforeLoad, onError: onBeforeError,
  } = usePosterImage(beforeUrl);

  return (
    <div className={styles.frame} style={{ '--compare-pos': `${position}%` } as CSSProperties}>
      {(!afterLoaded || afterError) && placeholder && (
        <div className={styles.placeholder}>{placeholder}</div>
      )}

      {!afterError && (
        <img
          key={afterKey}
          ref={afterRef}
          src={afterUrl}
          alt={alt}
          className={`${styles.image} ${afterLoaded ? styles.loaded : ''}`}
          onLoad={onAfterLoad}
          onError={onAfterError}
        />
      )}

      {!beforeError && (
        <div className={styles.beforeClip}>
          <img
            key={beforeKey}
            ref={beforeRef}
            src={beforeUrl}
            alt={`${alt} — original`}
            className={`${styles.image} ${beforeLoaded ? styles.loaded : ''}`}
            onLoad={onBeforeLoad}
            onError={onBeforeError}
          />
        </div>
      )}

      <div className={styles.divider} aria-hidden="true">
        <span className={styles.knob} />
      </div>

      <span className={`${styles.label} ${styles.labelBefore}`} aria-hidden="true">Before</span>
      <span className={`${styles.label} ${styles.labelAfter}`} aria-hidden="true">After</span>

      <input
        type="range"
        min={0}
        max={100}
        value={position}
        onChange={(e) => setPosition(e.currentTarget.valueAsNumber)}
        className={styles.range}

        aria-label={`Reveal the original poster for ${alt}`}
        aria-valuetext={`${Math.round(position)}% original`}
      />
    </div>
  );
}
