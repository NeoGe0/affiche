import { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { errorMessage, libraryApi } from '../../api';
import { useToast } from '../../context/ToastContext';
import type { ItemEpisode } from '../../types';
import { formatDate, formatDateTime, formatFileSize } from './format';

import styles from './ItemTable.module.css';
import headerStyles from './EpisodeList.module.css';

interface EpisodeListProps {

  showId: number;
  libraryId: number;
  showTitle: string;
  seasonNumber: number;
  mediaServerId?: number;
  onBack: () => void;
}

function episodeCode(seasonNumber: number, episodeNumber: number): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `S${pad(seasonNumber)}E${pad(episodeNumber)}`;
}

export function EpisodeList({
  showId,
  libraryId,
  showTitle,
  seasonNumber,
  mediaServerId,
  onBack,
}: EpisodeListProps) {
  const toast = useToast();
  const [episodes, setEpisodes] = useState<ItemEpisode[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (mediaServerId == null) return;
    let cancelled = false;

    setIsLoading(true);
    void (async () => {
      try {
        const data = await libraryApi.getSeasonEpisodes(mediaServerId, libraryId, showId, seasonNumber);
        if (!cancelled) setEpisodes(data);
      } catch (err) {
        if (cancelled) return;

        setEpisodes([]);
        toast.error(errorMessage(err, 'Could not load the episodes of this season.'),
          { title: 'Episodes' });
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [mediaServerId, libraryId, showId, seasonNumber, toast]);

  return (
    <div>
      <div className={headerStyles.header}>
        <button className={headerStyles.backButton} onClick={onBack}>
          <ArrowLeft size={16} /> Back
        </button>
        <h2 className={headerStyles.title}>
          {showTitle}{' '}
          <span className={headerStyles.seasonSuffix}>· Season {seasonNumber}</span>
        </h2>
      </div>

      {isLoading ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <span>Loading episodes...</span>
        </div>
      ) : episodes.length === 0 ? (
        <div className={styles.empty}>
          <p>No episodes tracked for this season</p>
          <p className="text-muted">
            Enable “Track episodes” for this library (Settings → Media Servers) and re-sync to see
            per-episode details here.
          </p>
        </div>
      ) : (
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.colNarrow}>Episode</th>
                <th>Title</th>
                <th>Air date</th>
                <th className={styles.colNarrow}>Resolution</th>
                <th className={styles.colNarrow}>Codec</th>
                <th className={styles.colNarrow}>Size</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {episodes.map((ep) => (
                <tr key={ep.id} className={styles.row}>
                  <td className={styles.colNarrow}>{episodeCode(ep.season_number, ep.episode_number)}</td>
                  <td className={styles.titleCell} title={ep.title}>{ep.title}</td>
                  <td>{formatDate(ep.air_date ?? undefined)}</td>
                  <td className={`${styles.colNarrow} ${styles.quality}`}>{ep.media_resolution || '—'}</td>
                  <td className={`${styles.colNarrow} ${styles.quality}`}>{ep.video_codec ? ep.video_codec.toUpperCase() : '—'}</td>
                  <td className={`${styles.colNarrow} ${styles.quality}`}>{formatFileSize(ep.media_size_bytes ?? undefined)}</td>
                  <td>{formatDateTime(ep.added_at ?? undefined)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
