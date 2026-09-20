import { useState, type ReactNode } from 'react';
import { usePosterImage } from '../../hooks';
import styles from './PosterFade.module.css';

interface PosterFadeProps {

  beforeUrl: string;

  afterUrl: string;

  alt: string;

  placeholder?: ReactNode;
}

export function PosterFade({ beforeUrl, afterUrl, alt, placeholder }: PosterFadeProps) {
  const [affiche, setAffiche] = useState(100);

  const {
    isLoaded: afterLoaded, isError: afterError, imgKey: afterKey, imgRef: afterRef,
    onLoad: onAfterLoad, onError: onAfterError,
  } = usePosterImage(afterUrl);
  const {
    isLoaded: beforeLoaded, isError: beforeError, imgKey: beforeKey, imgRef: beforeRef,
    onLoad: onBeforeLoad, onError: onBeforeError,
  } = usePosterImage(beforeUrl);

  return (
    <div className={styles.root}>
      <div className={styles.frame}>
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
          <img
            key={beforeKey}
            ref={beforeRef}
            src={beforeUrl}
            alt={`${alt} — original`}
            className={styles.image}
            style={{ opacity: beforeLoaded ? 1 - affiche / 100 : 0 }}
            onLoad={onBeforeLoad}
            onError={onBeforeError}
          />
        )}
      </div>

      <div className={styles.control}>
        <span className={affiche < 50 ? styles.labelOn : styles.label} aria-hidden="true">Original</span>
        <input
          type="range"
          min={0}
          max={100}
          value={affiche}
          onChange={(e) => setAffiche(e.currentTarget.valueAsNumber)}
          className={styles.range}
          aria-label={`Fade between the original poster and the Affiche poster for ${alt}`}
          aria-valuetext={`${Math.round(affiche)}% Affiche`}
        />
        <span className={affiche >= 50 ? styles.labelOn : styles.label} aria-hidden="true">Affiche</span>
      </div>
    </div>
  );
}
