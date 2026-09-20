import { libraryApi } from '../../api';
import { usePosterImage } from '../../hooks';
import type { ItemStats } from '../../types';
import { CoverageMeter } from './CoverageMeter';
import type { StagePoster } from './stagePoster';
import styles from './LibraryStage.module.css';

interface LibraryStageProps {
  libraryName: string;
  poster: StagePoster | null;

  stats?: ItemStats;

  autoUpload?: boolean;
  serverName?: string;
  onChangeAutoUpload?: () => void;

  runPercent?: number | null;
  onOpenPoster: (poster: StagePoster) => void;
}

export function LibraryStage({
  libraryName, poster, stats, autoUpload, serverName, onChangeAutoUpload, runPercent, onOpenPoster,
}: LibraryStageProps) {
  const running = runPercent != null;
  const url = poster
    ? libraryApi.getItemPosterUrl(poster.libraryId, poster.itemId, poster.posterVersion, 'thumb')
    : '';
  const { isLoaded, isError, imgKey, imgRef, onLoad, onError } = usePosterImage(url);

  if (!poster && !running && !stats && autoUpload === undefined) return null;

  const caption = poster?.reason === 'generated' ? 'Just generated' : `Latest poster in ${libraryName}`;

  return (
    <section className={styles.stage} aria-label={`${libraryName} poster stage`}>
      {poster && !isError && (
        <img key={`ambient-${imgKey}`} className={styles.ambient} src={url} alt="" aria-hidden="true" />
      )}

      <div className={styles.inner}>
        {poster && (
          <button
            type="button"
            className={styles.frame}
            onClick={() => onOpenPoster(poster)}
            aria-label={`Open ${poster.title}`}
          >
            {!isError && (
              <img
                key={imgKey}
                ref={imgRef}
                src={url}
                alt=""
                className={`${styles.image} ${isLoaded ? styles.revealed : ''}`}
                onLoad={onLoad}
                onError={onError}
              />
            )}
          </button>
        )}

        <div className={styles.text}>
          {poster && (
            <>
              <span className={styles.caption}>{caption}</span>
              <button type="button" className={styles.title} onClick={() => onOpenPoster(poster)}>
                {poster.title}
              </button>
            </>
          )}
          {stats && (
            <div className={styles.coverage}>
              <CoverageMeter label={libraryName} stats={stats} variant="stage" />
            </div>
          )}
          {autoUpload !== undefined && (
            <div className={styles.autoUpload}>
              <span className={`${styles.autoUploadState} ${autoUpload ? styles.on : ''}`}>
                <span className={styles.autoUploadDot} aria-hidden="true" />
                {autoUpload
                  ? `New posters go straight to ${serverName || 'the media server'}`
                  : 'New posters stay in Affiche until you upload them'}
              </span>
              {onChangeAutoUpload && (
                <button type="button" className={styles.autoUploadChange} onClick={onChangeAutoUpload}>
                  Change
                </button>
              )}
            </div>
          )}
          {running && (
            <div className={styles.run}>
              <span className={styles.runLabel}>Generating posters · {runPercent}%</span>
              <span
                className={styles.track}
                role="progressbar"
                aria-valuenow={runPercent}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Generation progress"
              >
                <span className={styles.fill} style={{ transform: `scaleX(${runPercent / 100})` }} />
              </span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
