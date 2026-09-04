import { useState, useEffect, useEffectEvent } from 'react';
import { ArrowLeft, RefreshCw, Image, RotateCcw, ExternalLink, CheckCircle, Circle, Loader2, Images, Upload, AlertTriangle, Lock, Unlock, Columns2, Maximize2, ChevronDown, ChevronUp } from 'lucide-react';
import { errorMessage, libraryApi } from '../../api';
import type { PosterVariant } from '../../api/libraries';
import { useToast } from '../../context/ToastContext';
import { usePosterImage } from '../../hooks';
import type { LibraryItem, LibraryItemWithSeasons, ItemSeason } from '../../types';
import { activationProps } from '../common';
import { PosterCompareSlider } from '../image';
import { PosterCompareModal } from './PosterCompareModal';
import { errorCauseCopy } from './errorCause';
import styles from './ItemDetail.module.css';
import {
  formatDateTime, canReset, posterSource, posterStatus, hasQuality, formatFileSize, formatBitrate,
  formatAudio,
} from './format';

interface ItemDetailProps {
  item: LibraryItem;
  mediaServerId?: number;
  onBack: () => void;
  onSync: () => void;
  onGeneratePoster: () => void;
  onReset: () => void;
  onSelectPoster: () => void;
  onUpload: () => void;
  onToggleLock: () => void;
  onSeasonSelectPoster?: (season: ItemSeason) => void;
  onSeasonClick?: (season: ItemSeason) => void;
  isLoading?: boolean;
  isUploading?: boolean;
  statusMessage?: string | null;
  imageRefreshKey?: number;
}

export function ItemDetail({
  item,
  mediaServerId,
  onBack,
  onSync,
  onGeneratePoster,
  onReset,
  onSelectPoster,
  onUpload,
  onToggleLock,
  onSeasonSelectPoster,
  onSeasonClick,
  isLoading,
  isUploading,
  statusMessage,
  imageRefreshKey = 0
}: ItemDetailProps) {
  const toast = useToast();

  const [seasonsState, setSeasonsState] =
    useState<{ itemId: number; data: LibraryItemWithSeasons | null } | null>(null);

  const canCompare = item.source_poster_version != null;
  const [comparingItemId, setComparingItemId] = useState<number | null>(null);
  const comparing = canCompare && comparingItemId === item.id;
  const setComparing = (next: boolean | ((on: boolean) => boolean)) =>
    setComparingItemId((typeof next === 'function' ? next(comparing) : next) ? item.id : null);

  const [fullSizeCompare, setFullSizeCompare] =
    useState<{ title: string; beforeUrl: string; afterUrl: string } | null>(null);

  const itemPosterUrl = (version: string | null | undefined, variant: PosterVariant) =>
    libraryApi.getItemPosterUrl(item.library_id, item.id, version, 'full', variant);

  const isShow = item.type === 'show';
  const hasSeasonsForItem = seasonsState?.itemId === item.id;
  const isLoadingSeasons = isShow && !!mediaServerId && !hasSeasonsForItem;
  const seasons = (hasSeasonsForItem ? seasonsState.data?.seasons : undefined) ?? [];

  const seasonsFailed = hasSeasonsForItem && seasonsState.data === null;

  const reportSeasonsFailure = useEffectEvent((itemId: number, error: unknown) => {

    if (hasSeasonsForItem) return;
    setSeasonsState({ itemId, data: null });
    toast.error(errorMessage(error, 'Could not load the seasons for this show.'), {
      title: 'Seasons',
    });
  });

  useEffect(() => {
    if (!(isShow && mediaServerId)) return;
    let cancelled = false;
    const load = async () => {
      try {
        const data = await libraryApi.getItemWithSeasons(mediaServerId, item.library_id, item.id);
        if (!cancelled) setSeasonsState({ itemId: item.id, data });
      } catch (error) {
        if (!cancelled) reportSeasonsFailure(item.id, error);
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [item.id, item.library_id, isShow, mediaServerId, imageRefreshKey]);

  return (
    <div className={styles.container}>
      <button className={styles.backButton} onClick={onBack}>
        <ArrowLeft size={20} />
        Back to library
      </button>

      {isLoading && (
        <div className={styles.loadingBanner}>
          <Loader2 size={18} className={styles.spinner} />
          <span>{statusMessage || 'Processing...'}</span>
        </div>
      )}

      <div className={styles.header}>
        <div className={styles.posterContainer}>
          <div className={styles.posterFrame}>
            <ItemPoster
              mediaServerId={mediaServerId}
              libraryId={item.library_id}
              itemId={item.id}
              title={item.title}
              hasPoster={!!item.has_poster || item.poster_version != null}
              version={item.poster_version}
              sourceVersion={item.source_poster_version}
              comparing={comparing}
            />
            {canCompare && (

              <button
                className={styles.expandButton}
                onClick={() => setFullSizeCompare({
                  title: item.title,
                  beforeUrl: itemPosterUrl(item.source_poster_version, 'source'),
                  afterUrl: itemPosterUrl(item.poster_version, 'generated'),
                })}
                title="Compare full size"
                aria-label={`Compare ${item.title} full size`}
              >
                <Maximize2 size={14} />
              </button>
            )}
          </div>
          {canCompare && (
            <button
              className={styles.compareToggle}
              onClick={() => setComparing((on) => !on)}
              aria-pressed={comparing}
            >
              <Columns2 size={14} />
              {comparing ? 'Show poster' : 'Compare with original'}
            </button>
          )}
        </div>

        <div className={styles.info}>
          <h1 className={styles.title}>{item.title}</h1>
          {item.year && <p className={styles.year}>{item.year}</p>}

          {item.error_message && <FailureBanner item={item} />}

          <div className={styles.metadata}>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Status</span>
              <span className={item.error_message ? styles.failed : item.processed ? styles.processed : styles.pending}>
                {item.error_message ? 'Failed' : item.processed ? 'Processed' : 'Pending'}
              </span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Type</span>
              <span className={styles.metaValue}>{item.type === 'show' ? 'TV Show' : 'Movie'}</span>
            </div>
            {item.tmdb_id && (
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>TMDB</span>
                <a
                  href={`https://www.themoviedb.org/${item.type === 'movie' ? 'movie' : 'tv'}/${item.tmdb_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.link}
                >
                  {item.tmdb_id} <ExternalLink size={12} />
                </a>
              </div>
            )}
            {item.imdb_id && (
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>IMDB</span>
                <a
                  href={`https://www.imdb.com/title/${item.imdb_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.link}
                >
                  {item.imdb_id} <ExternalLink size={12} />
                </a>
              </div>
            )}
            {item.tvdb_id && (
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>TVDB</span>
                <a
                  href={`https://www.thetvdb.com/dereferrer/${item.type === 'movie' ? 'movie' : 'series'}/${item.tvdb_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.link}
                >
                  {item.tvdb_id} <ExternalLink size={12} />
                </a>
              </div>
            )}
          </div>

          {}
          <div className={styles.metadata}>
            <span className={styles.metaHeading}>Details</span>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Poster</span>
              <span className={styles.metaValue}>{posterStatus(item)}</span>
            </div>
            {item.poster_provider && (
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Source</span>
                <span className={styles.metaValue}>{posterSource(item.poster_provider)}</span>
              </div>
            )}
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Added</span>
              <span className={styles.metaValue}>{formatDateTime(item.added_at)}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Updated</span>
              <span className={styles.metaValue}>{formatDateTime(item.updated_at)}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Last seen</span>
              <span className={styles.metaValue}>{formatDateTime(item.last_seen_at)}</span>
            </div>
            {item.external_id && (
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Server ID</span>
                <span className={styles.metaValue}>{item.external_id}</span>
              </div>
            )}
          </div>

          {}
          {hasQuality(item) && (
            <div className={styles.metadata}>
              <span className={styles.metaHeading}>Quality</span>
              {(item.media_resolution || item.media_height) && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Resolution</span>
                  <span className={styles.metaValue}>
                    {item.media_resolution || `${item.media_height}p`}
                    {item.media_width && item.media_height ? ` (${item.media_width}×${item.media_height})` : ''}
                  </span>
                </div>
              )}
              {item.video_codec && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Video</span>
                  <span className={styles.metaValue}>{item.video_codec.toUpperCase()}</span>
                </div>
              )}
              {(item.audio_codec || item.audio_channels) && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Audio</span>
                  <span className={styles.metaValue}>{formatAudio(item)}</span>
                </div>
              )}
              {item.media_container && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Container</span>
                  <span className={styles.metaValue}>{item.media_container.toUpperCase()}</span>
                </div>
              )}
              {item.media_bitrate != null && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Bitrate</span>
                  <span className={styles.metaValue}>{formatBitrate(item.media_bitrate)}</span>
                </div>
              )}
              {item.media_size_bytes != null && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Size</span>
                  <span className={styles.metaValue}>{formatFileSize(item.media_size_bytes)}</span>
                </div>
              )}
            </div>
          )}

          <div className={styles.actions}>
            <button
              className={styles.actionButton}
              onClick={onSync}
              disabled={isLoading}
            >
              <RefreshCw size={16} />
              Sync Metadata
            </button>
            <button
              className={`${styles.actionButton} ${styles.primary}`}
              onClick={onGeneratePoster}
              disabled={isLoading}
            >
              <Image size={16} />
              Generate Poster
            </button>
            <button
              className={styles.actionButton}
              onClick={onSelectPoster}
              disabled={isLoading}
            >
              <Images size={16} />
              Select Poster
            </button>
            <button
              className={styles.actionButton}
              onClick={onUpload}
              disabled={isLoading || isUploading || !item.processed}
              title={item.processed ? 'Upload this poster to the media server' : 'Generate a poster first'}
            >
              {isUploading ? <Loader2 size={16} className={styles.spinner} /> : <Upload size={16} />}
              Upload
            </button>
            <button
              className={styles.actionButton}
              onClick={onToggleLock}
              disabled={isLoading}
              aria-pressed={item.locked}
              title={
                item.locked
                  ? 'Unlock — poster generation will regenerate this item again'
                  : 'Lock — keep this poster; generation will skip this item'
              }
            >
              {item.locked ? <Lock size={16} /> : <Unlock size={16} />}
              {item.locked ? 'Locked' : 'Lock Poster'}
            </button>
            <button
              className={`${styles.actionButton} ${styles.danger}`}
              onClick={onReset}
              disabled={isLoading || !canReset(item)}
            >
              <RotateCcw size={16} />
              Reset Poster
            </button>
          </div>
        </div>
      </div>

      {isShow && (
        <div className={styles.seasonsSection}>
          <h2 className={styles.seasonsTitle}>Seasons</h2>
          {isLoadingSeasons ? (
            <div className={styles.loading}>Loading seasons...</div>
          ) : seasonsFailed ? (
            <div className={styles.empty}>Could not load seasons.</div>
          ) : seasons.length === 0 ? (
            <div className={styles.empty}>No seasons found</div>
          ) : (
            <div className={styles.seasonsGrid}>
              {seasons.map((season) => (
                <SeasonCard
                  key={season.id}
                  season={season}
                  mediaServerId={mediaServerId}
                  libraryId={item.library_id}
                  showId={item.id}
                  onSelectPoster={onSeasonSelectPoster ? () => onSeasonSelectPoster(season) : undefined}
                  onCardClick={onSeasonClick ? () => onSeasonClick(season) : undefined}
                  onCompare={() => setFullSizeCompare({
                    title: `${item.title} — ${season.title}`,

                    beforeUrl: libraryApi.getSeasonPosterUrl(
                      item.library_id, item.id, season.season_number,
                      season.source_poster_version, 'full', 'source'),
                    afterUrl: libraryApi.getSeasonPosterUrl(
                      item.library_id, item.id, season.season_number, season.poster_version, 'full'),
                  })}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {fullSizeCompare && (
        <PosterCompareModal {...fullSizeCompare} onClose={() => setFullSizeCompare(null)} />
      )}
    </div>
  );
}

function FailureBanner({ item }: { item: LibraryItem }) {
  const [showFix, setShowFix] = useState(false);
  const cause = errorCauseCopy(item);

  return (
    <div className={styles.errorBanner}>
      <AlertTriangle size={16} />
      <div className={styles.errorBody}>
        <span>{item.error_message}</span>
        {cause && (
          <>
            {
}
            <button
              type="button"
              className={styles.errorCause}
              onClick={() => setShowFix(!showFix)}
              aria-expanded={showFix}
            >
              <span>{cause.summary}</span>
              {showFix ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showFix && (
              <div className={styles.errorFix}>
                <p>{cause.detail}</p>
                <ol>
                  {cause.steps.map((step) => <li key={step}>{step}</li>)}
                </ol>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

interface ItemPosterProps {
  mediaServerId?: number;
  libraryId: number;
  itemId: number;
  title: string;
  hasPoster?: boolean;
  version?: string | null;
  variant?: PosterVariant;

  sourceVersion?: string | null;
  comparing?: boolean;
}

function ItemPoster({
  mediaServerId, libraryId, itemId, title, hasPoster = false, version, variant = 'generated',
  sourceVersion, comparing = false,
}: ItemPosterProps) {

  const imageUrl = mediaServerId
    ? libraryApi.getItemPosterUrl(libraryId, itemId, version, 'full', variant)
    : '';

  const { isLoaded, isError, imgKey, imgRef, onLoad, onError } = usePosterImage(imageUrl);

  if (comparing && mediaServerId) {
    return (
      <div className={styles.poster}>
        <PosterCompareSlider
          beforeUrl={libraryApi.getItemPosterUrl(libraryId, itemId, sourceVersion, 'full', 'source')}
          afterUrl={imageUrl}
          alt={title}
          placeholder={<span>{title.charAt(0)}</span>}
        />
      </div>
    );
  }

  return (
    <div className={styles.poster}>
      {(!isLoaded || isError) && (
        <div className={styles.placeholder}>
          <span>{title.charAt(0)}</span>
        </div>
      )}
      {hasPoster && !isError && mediaServerId && (
        <img
          key={imgKey}
          ref={imgRef}
          src={imageUrl}
          alt={title}
          className={`${styles.posterImage} ${isLoaded ? styles.loaded : ''}`}
          onLoad={onLoad}
          onError={onError}
        />
      )}
    </div>
  );
}

interface SeasonCardProps {
  season: ItemSeason;
  mediaServerId?: number;
  libraryId: number;
  showId: number;
  onSelectPoster?: () => void;
  onCardClick?: () => void;
  onCompare?: () => void;
}

function SeasonCard({
  season, mediaServerId, libraryId, showId, onSelectPoster, onCardClick, onCompare,
}: SeasonCardProps) {

  const imageUrl = mediaServerId
    ? libraryApi.getSeasonPosterUrl(
        libraryId,
        showId,
        season.season_number,
        season.poster_version,
        'thumb'
      )
    : '';

  const { isLoaded, isError, imgKey, imgRef, onLoad, onError } = usePosterImage(imageUrl);

  return (
    <div
      className={`${styles.seasonCard} ${onCardClick ? styles.seasonCardClickable : ''}`}
      {...activationProps(onCardClick)}
      title={onCardClick ? 'View episodes' : undefined}
    >
      <div className={styles.seasonPoster}>
        {(!isLoaded || isError) && (
          <div className={styles.seasonPlaceholder}>
            <span>S{season.season_number}</span>
          </div>
        )}
        {season.has_poster && !isError && mediaServerId && (
          <img
            key={imgKey}
            ref={imgRef}
            src={imageUrl}
            alt={season.title}
            className={`${styles.seasonImage} ${isLoaded ? styles.loaded : ''}`}
            onLoad={onLoad}
            onError={onError}
          />
        )}
        <div className={styles.seasonStatus}>
          {season.processed ? (
            <CheckCircle size={16} className={styles.processed} />
          ) : (
            <Circle size={16} className={styles.pending} />
          )}
        </div>
      </div>
      <div className={styles.seasonInfo}>
        <div className={styles.seasonHeader}>
          <span className={styles.seasonNumber}>Season {season.season_number}</span>
          {

}
          {onCompare && season.source_poster_version != null && (
            <button
              className={styles.seasonSelectButton}
              onClick={(e) => { e.stopPropagation(); onCompare(); }}
              title="Compare with original"
              aria-label={`Compare ${season.title} with the original`}
            >
              <Columns2 size={14} />
            </button>
          )}
          {onSelectPoster && (
            <button
              className={styles.seasonSelectButton}
              onClick={(e) => { e.stopPropagation(); onSelectPoster(); }}
              title="Select poster"
            >
              <Images size={14} />
            </button>
          )}
        </div>
        <span className={styles.seasonTitle}>{season.title}</span>
      </div>
    </div>
  );
}
