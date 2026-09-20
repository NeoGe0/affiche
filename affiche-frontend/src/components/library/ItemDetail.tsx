import { useState, useEffect, useEffectEvent, type ReactNode } from 'react';
import { ArrowLeft, ChevronLeft, ChevronRight, RefreshCw, Image, RotateCcw, ExternalLink, CheckCircle, Circle, Loader2, Images, Upload, AlertTriangle, Lock, Unlock, Columns2, ChevronDown, ChevronUp } from 'lucide-react';
import { errorMessage, libraryApi } from '../../api';
import type { PosterVariant } from '../../api/libraries';
import { useToast } from '../../context/ToastContext';
import { usePosterImage } from '../../hooks';
import type { LibraryItem, LibraryItemWithSeasons, ItemSeason } from '../../types';
import { OverflowMenu } from '../common';
import { PosterFade } from '../image';
import { ItemArtworkStrip } from './ItemArtworkStrip';
import { PosterCompareModal } from './PosterCompareModal';
import { posterTargetFromItem } from './posterTarget';
import { errorCauseCopy } from './errorCause';
import styles from './ItemDetail.module.css';
import {
  formatDateTime, canReset, posterStatusDetail, hasQuality, formatFileSize, formatBitrate,
  formatAudio,
} from './format';
import { detailsSummary, POSTER_STATE_LABEL, posterState, primaryPosterAction } from './posterState';

interface ItemDetailProps {
  item: LibraryItem;
  mediaServerId?: number;

  mediaServerName?: string;
  onBack: () => void;

  previousItem?: { title: string };
  nextItem?: { title: string };
  onPrevious?: () => void;
  onNext?: () => void;
  onSync: () => void;
  onGeneratePoster: () => void;

  uploadsAutomatically?: boolean;
  onReset: () => void;

  onSelectPoster: (posterUrl?: string) => void;
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
  mediaServerName,
  onBack,
  previousItem,
  nextItem,
  onPrevious,
  onNext,
  onSync,
  onGeneratePoster,
  uploadsAutomatically,
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

  const stepWithKeys = useEffectEvent((event: KeyboardEvent) => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const target = event.target as HTMLElement | null;
    if (target instanceof Element && target.closest('input, textarea, select, [contenteditable="true"], [role="dialog"]')) return;
    if (event.key === 'ArrowLeft' && previousItem && onPrevious) onPrevious();
    if (event.key === 'ArrowRight' && nextItem && onNext) onNext();
  });

  useEffect(() => {
    const listener = (event: KeyboardEvent) => stepWithKeys(event);
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);

  const state = posterState(item);
  const primary = primaryPosterAction(item);
  const statusDetail = posterStatusDetail(item);
  const hasPoster = !!item.has_poster || item.poster_version != null;
  const serverName = mediaServerName || 'the media server';
  const kind = isShow ? 'show' : 'movie';

  return (
    <div className={styles.container}>
      <div className={styles.topBar}>
        <button className={styles.backButton} onClick={onBack}>
          <ArrowLeft size={20} />
          Back to library
        </button>
        {(previousItem || nextItem) && (
          <nav className={styles.stepper} aria-label="Other items in this listing">
            <button
              className={styles.stepButton}
              onClick={onPrevious}
              disabled={!previousItem}
              title={previousItem ? `Previous: ${previousItem.title} (←)` : undefined}
            >
              <ChevronLeft size={16} />
              <span className={styles.stepLabel}>{previousItem ? previousItem.title : 'Previous'}</span>
            </button>
            <button
              className={styles.stepButton}
              onClick={onNext}
              disabled={!nextItem}
              title={nextItem ? `Next: ${nextItem.title} (→)` : undefined}
            >
              <span className={styles.stepLabel}>{nextItem ? nextItem.title : 'Next'}</span>
              <ChevronRight size={16} />
            </button>
          </nav>
        )}
      </div>

      {isLoading && (
        <div className={styles.loadingBanner}>
          <Loader2 size={18} className="spin" />
          <span>{statusMessage || 'Processing…'}</span>
        </div>
      )}

      <div className={styles.header}>
        {hasPoster && mediaServerId && (
          <img
            className={styles.ambient}
            src={itemPosterUrl(item.poster_version, 'generated')}
            alt=""
            aria-hidden="true"
          />
        )}

        <div className={styles.posterContainer}>
          {canCompare && mediaServerId ? (
            <PosterFade
              beforeUrl={itemPosterUrl(item.source_poster_version, 'source')}
              afterUrl={itemPosterUrl(item.poster_version, 'generated')}
              alt={item.title}
              placeholder={<span>{item.title.charAt(0)}</span>}
            />
          ) : (
            <ItemPoster
              mediaServerId={mediaServerId}
              libraryId={item.library_id}
              itemId={item.id}
              title={item.title}
              hasPoster={hasPoster}
              version={item.poster_version}
            />
          )}
        </div>

        <div className={styles.info}>
          <h1 className={styles.title}>{item.title}</h1>
          <p className={styles.year}>
            {[item.year, isShow ? 'TV show' : 'Movie'].filter(Boolean).join(' · ')}
          </p>

          <div className={styles.statusRow}>
            <span className={`${styles.statusPill} ${styles[state]}`}>
              <span className={styles.statusDot} aria-hidden="true" />
              {POSTER_STATE_LABEL[state]}
            </span>
            {item.locked && (
              <span className={styles.statusPill}>
                <Lock size={13} aria-hidden="true" />
                Locked
              </span>
            )}
          </div>
          {statusDetail && <p className={styles.statusDetail}>{statusDetail}</p>}

          {item.error_message && <FailureBanner item={item} />}

          <div className={styles.primaryBlock}>
            {primary === 'upload' && (
              <>
                <button
                  className={`${styles.actionButton} ${styles.primary}`}
                  onClick={onUpload}
                  disabled={isLoading || isUploading}
                >
                  {isUploading ? <Loader2 size={16} className="spin" /> : <Upload size={16} />}
                  Upload to {mediaServerName || 'media server'}
                </button>
                <p className={styles.consequence}>
                  Replaces the poster {serverName} shows for this {kind}. The artwork it has now is
                  kept, so Reset puts it back.
                </p>
              </>
            )}
            {primary === 'generate' && (
              <>
                <button
                  className={`${styles.actionButton} ${styles.primary}`}
                  onClick={onGeneratePoster}
                  disabled={isLoading}
                >
                  <Image size={16} />
                  Generate poster
                </button>
                <p className={styles.consequence}>
                  {uploadsAutomatically === undefined
                    ? "Uses this library's style, and follows its upload setting."
                    : uploadsAutomatically
                      ? `Uses this library's style and goes straight to ${serverName}, which keeps its current artwork for Reset.`
                      : "Uses this library's style. The poster stays in Affiche until you upload it."}
                </p>
              </>
            )}
            {primary === 'choose' && (
              <button
                className={`${styles.actionButton} ${styles.primary}`}
                onClick={() => onSelectPoster()}
                disabled={isLoading}
              >
                <Images size={16} />
                Choose artwork
              </button>
            )}
          </div>

          <div className={styles.actions}>
            {primary !== 'choose' && (
              <button className={styles.actionButton} onClick={() => onSelectPoster()} disabled={isLoading}>
                <Images size={16} />
                Choose artwork
              </button>
            )}
            {primary !== 'generate' && !item.locked && (
              <button className={styles.actionButton} onClick={onGeneratePoster} disabled={isLoading}>
                <RefreshCw size={16} />
                Regenerate
              </button>
            )}
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
              {item.locked ? <Unlock size={16} /> : <Lock size={16} />}
              {item.locked ? 'Unlock' : 'Lock'}
            </button>
            <OverflowMenu
              title="More actions"
              triggerClassName={styles.actionButton}
              items={[
                { icon: <RefreshCw size={16} />, label: 'Sync metadata', onClick: onSync, disabled: isLoading },
                {
                  icon: <RotateCcw size={16} />,
                  label: 'Reset poster',
                  onClick: onReset,
                  disabled: isLoading || !canReset(item),
                  danger: true,
                },
              ]}
            />
          </div>

          <ItemArtworkStrip
            key={item.id}
            target={posterTargetFromItem(item)}
            onPick={onSelectPoster}
          />

          <details className={styles.details}>
            <summary className={styles.detailsSummary}>
              <span className={styles.detailsHeading}>Details</span>
              <span className={styles.detailsLine}>{detailsSummary(item)}</span>
            </summary>
            <ItemFacts item={item} />
          </details>
        </div>
      </div>

      {isShow && (
        <div className={styles.seasonsSection}>
          <h2 className={styles.seasonsTitle}>Seasons</h2>
          {isLoadingSeasons ? (
            <div className={styles.loading}>Loading seasons…</div>
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

function ItemFacts({ item }: { item: LibraryItem }) {
  return (
    <div className={styles.facts}>
      <dl className={styles.metadata}>
        {item.tmdb_id && (
          <Fact label="TMDB">
            <a
              href={`https://www.themoviedb.org/${item.type === 'movie' ? 'movie' : 'tv'}/${item.tmdb_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              {item.tmdb_id} <ExternalLink size={12} />
            </a>
          </Fact>
        )}
        {item.imdb_id && (
          <Fact label="IMDB">
            <a
              href={`https://www.imdb.com/title/${item.imdb_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              {item.imdb_id} <ExternalLink size={12} />
            </a>
          </Fact>
        )}
        {item.tvdb_id && (
          <Fact label="TVDB">
            <a
              href={`https://www.thetvdb.com/dereferrer/${item.type === 'movie' ? 'movie' : 'series'}/${item.tvdb_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              {item.tvdb_id} <ExternalLink size={12} />
            </a>
          </Fact>
        )}
        <Fact label="Added">{formatDateTime(item.added_at)}</Fact>
        <Fact label="Updated">{formatDateTime(item.updated_at)}</Fact>
        <Fact label="Last seen">{formatDateTime(item.last_seen_at)}</Fact>
        {item.external_id && <Fact label="Server ID">{item.external_id}</Fact>}
      </dl>

      {}
      {hasQuality(item) && (
        <dl className={styles.metadata}>
          {(item.media_resolution || item.media_height) && (
            <Fact label="Resolution">
              {item.media_resolution || `${item.media_height}p`}
              {item.media_width && item.media_height ? ` (${item.media_width}×${item.media_height})` : ''}
            </Fact>
          )}
          {item.video_codec && <Fact label="Video">{item.video_codec.toUpperCase()}</Fact>}
          {(item.audio_codec || item.audio_channels) && <Fact label="Audio">{formatAudio(item)}</Fact>}
          {item.media_container && <Fact label="Container">{item.media_container.toUpperCase()}</Fact>}
          {item.media_bitrate != null && <Fact label="Bitrate">{formatBitrate(item.media_bitrate)}</Fact>}
          {item.media_size_bytes != null && <Fact label="Size">{formatFileSize(item.media_size_bytes)}</Fact>}
        </dl>
      )}
    </div>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.metaItem}>
      <dt className={styles.metaLabel}>{label}</dt>
      <dd className={styles.metaValue}>{children}</dd>
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
}

function ItemPoster({ mediaServerId, libraryId, itemId, title, hasPoster = false, version }: ItemPosterProps) {

  const imageUrl = mediaServerId
    ? libraryApi.getItemPosterUrl(libraryId, itemId, version, 'full', 'generated')
    : '';

  const { isLoaded, isError, imgKey, imgRef, onLoad, onError } = usePosterImage(imageUrl);

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
      onClick={onCardClick}
    >
      {onCardClick && (
        <button
          type="button"
          className={styles.seasonOpen}
          onClick={(e) => { e.stopPropagation(); onCardClick(); }}
          aria-label={`View episodes of ${season.title}`}
        />
      )}
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
              aria-label={`Choose artwork for ${season.title}`}
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
