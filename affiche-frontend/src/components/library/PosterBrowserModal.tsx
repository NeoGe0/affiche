import { useState } from 'react';
import { Loader2 } from 'lucide-react';

import { errorMessage } from '../../api';
import { Modal } from '../common';
import { useToast } from '../../context/ToastContext';
import {
  usePosterBrowseQuery,
  usePosterCandidates,
  usePosterConfig,
  usePosterStyleDrafts,
  usePosterTitleDraft,
  useProviderStatus,
} from '../../hooks';
import { PosterBrowserToolbar } from './PosterBrowserToolbar';
import { PosterCandidateGrid } from './PosterCandidateGrid';
import { sortPosterCandidates } from './posterSort';
import { PosterPreviewPane } from './PosterPreviewPane';
import { PosterEditPanel } from './PosterEditPanel';
import type { PosterTarget } from './posterTarget';
import type { TmdbMatch } from '../../hooks/usePosterBrowseQuery';
import type { OverlayOptions, TextOptions } from '../../types';
import styles from './PosterBrowserModal.module.css';

interface PosterBrowserModalProps {

  target: PosterTarget;

  seasonNumber?: number;

  tmdbMatch?: TmdbMatch;

  onTmdbMatchChange?: (match: TmdbMatch) => Promise<void>;

  onTmdbMatchFind?: () => Promise<{ tmdbId: number; seasonNumber: number; reason: string } | null>;
  onClose: () => void;
  onSave: (
    posterUrl: string,
    opts: { overlayOptions?: OverlayOptions; textOptions?: TextOptions; jpegQuality?: number; title?: string; upload?: boolean }
  ) => void;
  isSaving?: boolean;

  defaultUpload?: boolean;

  canUpload?: boolean;

  initialPoster?: string;
}

export function PosterBrowserModal({
  target,
  seasonNumber,
  tmdbMatch,
  onTmdbMatchChange,
  onTmdbMatchFind,
  onClose,
  onSave,
  isSaving = false,
  defaultUpload = false,
  canUpload = true,
  initialPoster,
}: PosterBrowserModalProps) {
  const { config: posterConfig } = usePosterConfig();
  const { isAnyProviderConfigured, configuredProviders } = useProviderStatus();
  const toast = useToast();

  const { title: itemTitle, year, mediaType, tmdbId, tvdbId, collectionId } = target;
  const isSeason = seasonNumber !== undefined;
  const defaultTitle = isSeason ? `Season ${seasonNumber}` : itemTitle;

  const [selectedPoster, setSelectedPoster] = useState<string | null>(initialPoster ?? null);
  const [showEditPanel, setShowEditPanel] = useState(false);
  const [findOpen, setFindOpen] = useState(false);
  const [isSavingMatch, setIsSavingMatch] = useState(false);
  const [isFindingMatch, setIsFindingMatch] = useState(false);
  const [foundReason, setFoundReason] = useState<string | undefined>(undefined);

  const query = usePosterBrowseQuery({
    itemTitle,
    year,
    seasonNumber,
    tmdbMatch,
    onSourceChanged: () => setSelectedPoster(null),
  });

  const style = usePosterStyleDrafts(posterConfig);
  const { overlayOptions, textOptions, quality } = style;

  const titleDraft = usePosterTitleDraft({ defaultTitle, mediaType, tmdbId, tvdbId, seasonNumber });

  const candidates = usePosterCandidates({
    mediaType,
    tmdbId,
    tvdbId,
    collectionId,
    seasonNumber: isSeason && !query.useShowArt ? query.searchSeasonNumber : undefined,
    tmdbIdOverride: query.appliedTmdbMatch.tmdbId ?? undefined,
    tmdbSeasonNumberOverride: query.appliedTmdbMatch.seasonNumber ?? undefined,
    provider: query.provider,
    language: query.language,
  });

  const handleSearch = async () => {
    const name = query.searchTitle.trim();
    if (!name) return;
    if (await candidates.search(name, query.yearFilter)) {
      setSelectedPoster(null);
    }
  };

  const findTmdbMatch = async () => {
    if (!onTmdbMatchFind) return;
    setIsFindingMatch(true);
    setFoundReason(undefined);
    try {
      const found = await onTmdbMatchFind();
      if (!found) {
        setFoundReason('No confident match found. Fill the boxes yourself, or leave it as is.');
        return;
      }

      query.setTmdbIdDraft(String(found.tmdbId));
      query.setTmdbSeasonDraft(String(found.seasonNumber));
      setFoundReason(`${found.reason}. Press Save match to keep it.`);
    } catch (err) {
      toast.error(errorMessage(err, 'Could not work out a TMDB match.'));
    } finally {
      setIsFindingMatch(false);
    }
  };

  const persistTmdbMatch = async (match: TmdbMatch) => {
    if (!onTmdbMatchChange) return;
    setIsSavingMatch(true);
    try {
      await onTmdbMatchChange(match);
      toast.success(match.tmdbId === null
        ? 'TMDB match cleared for this season.'
        : `Season artwork now comes from TMDB series ${match.tmdbId}.`);
    } catch (err) {
      toast.error(errorMessage(err, 'Could not save the TMDB match.'));
    } finally {
      setIsSavingMatch(false);
    }
  };

  const stageCustom = async (params: { file?: File; url?: string }) => {
    const staged = await candidates.stageCustom(params);

    if (staged) setSelectedPoster(staged);
  };

  const titleLanguageEnabled = isAnyProviderConfigured && (tmdbId !== undefined || tvdbId !== undefined);

  const save = (posterUrl: string, upload: boolean) => {
    onSave(posterUrl, {
      overlayOptions,
      textOptions,
      jpegQuality: quality,
      title: titleDraft.title,
      upload,
    });
  };

  const handleSave = (upload: boolean) => {
    if (selectedPoster) save(selectedPoster, upload);
  };

  const saveFromGrid = (posterUrl: string) => {
    if (isSaving) return;
    setSelectedPoster(posterUrl);
    save(posterUrl, canUpload && defaultUpload);
  };

  const resetStyle = () => {
    const undo = style.reset();
    if (undo) toast.info('Style reset to defaults', { action: { label: 'Undo', onClick: undo } });
  };

  const isEditing = showEditPanel && !!overlayOptions && !!textOptions;
  const sortedPosters = sortPosterCandidates(candidates.posters, query.sort);

  const modalTitle = isSeason
    ? `Choose artwork for ${itemTitle}, season ${seasonNumber}`
    : `Choose artwork for ${itemTitle}`;

  return (
    <>
      {
}
      <Modal size="full" label={modalTitle} isBusy={isSaving} onClose={onClose}>
        <div className={styles.header}>
          <h2 className={styles.title}>{modalTitle}</h2>
        </div>

        <div className={styles.content}>
          {candidates.error && <div className={styles.error}>{candidates.error}</div>}

          <PosterBrowserToolbar
            search={{
              title: query.searchTitle,
              year: query.searchYear,
              onTitleChange: query.setSearchTitle,
              onYearChange: query.setSearchYear,
              onSubmit: handleSearch,
              isSearching: candidates.isSearching,
            }}
            filters={{
              language: query.language,
              onLanguageChange: query.changeLanguage,
              provider: query.provider,
              onProviderChange: query.changeProvider,
              availableProviders: configuredProviders,
              sort: query.sort,
              onSortChange: query.changeSort,
            }}
            custom={{
              url: query.customUrl,
              onUrlChange: query.setCustomUrl,
              onAddUrl: () => {
                const url = query.customUrl.trim();
                if (url) stageCustom({ url });
              },
              onPickFile: (file) => stageCustom({ file }),
              isStaging: candidates.isStagingCustom,
            }}
            find={{ isOpen: findOpen, onToggle: () => setFindOpen((open) => !open) }}
            resultCount={candidates.isLoading ? undefined : sortedPosters.length}
            seasonSource={
              isSeason
                ? {
                    seasonNumber: query.searchSeasonNumber,
                    onSeasonNumberChange: query.changeSearchSeasonNumber,
                    useShowArt: query.useShowArt,
                    onUseShowArtChange: query.changeUseShowArt,
                    appliesToSeason: seasonNumber,
                    tmdbMatch: onTmdbMatchChange
                      ? {
                          idDraft: query.tmdbIdDraft,
                          onIdDraftChange: query.setTmdbIdDraft,
                          seasonDraft: query.tmdbSeasonDraft,
                          onSeasonDraftChange: query.setTmdbSeasonDraft,
                          onApply: () => void persistTmdbMatch(query.applyTmdbMatch()),
                          onFind: onTmdbMatchFind ? () => void findTmdbMatch() : undefined,
                          isFinding: isFindingMatch,
                          foundReason,
                          isSaving: isSavingMatch,
                          isSet: query.appliedTmdbMatch.tmdbId !== null,
                          onClear: () => {
                            setFoundReason(undefined);
                            void persistTmdbMatch(query.clearTmdbMatch());
                          },
                        }
                      : undefined,
                  }
                : undefined
            }
          />

          <div className={styles.mainArea}>
            <PosterCandidateGrid
              posters={sortedPosters}
              selected={selectedPoster}
              isLoading={candidates.isLoading}
              onSelect={setSelectedPoster}
              onActivate={saveFromGrid}
              compact={isEditing}
              onFindElsewhere={findOpen ? undefined : () => setFindOpen(true)}
            />

            {isEditing ? (
              <PosterEditPanel
                imageUrl={selectedPoster}
                title={titleDraft.title}
                onTitleChange={titleDraft.changeTitle}
                titleLanguage={titleDraft.language}
                onTitleLanguageChange={titleDraft.changeLanguage}
                titleLanguageEnabled={titleLanguageEnabled}
                isTranslating={titleDraft.isTranslating}
                titleNotFound={titleDraft.notFound}
                overlayOptions={overlayOptions}
                textOptions={textOptions}
                jpegQuality={quality}
                onOverlayChange={style.changeOverlay}
                onTextChange={style.changeText}
                onQualityChange={style.changeQuality}
                onReset={resetStyle}
                onClose={() => setShowEditPanel(false)}
              />
            ) : (
              <PosterPreviewPane
                imageUrl={selectedPoster}
                title={titleDraft.title}
                overlayOptions={overlayOptions}
                textOptions={textOptions}
                onEditStyle={() => setShowEditPanel(true)}
              />
            )}
          </div>
        </div>

        <div className={styles.footer}>
          <button
            className={`${styles.footerButton} ${styles.cancel}`}
            onClick={onClose}
            disabled={isSaving}
          >
            Cancel
          </button>
          {isSaving ? (
            <button className={`${styles.footerButton} ${styles.save}`} disabled>
              <Loader2 size={16} className="spin" />
              Saving…
            </button>
          ) : (
            <>
              {}
              <button
                className={`${styles.footerButton} ${canUpload && defaultUpload ? styles.secondary : styles.save}`}
                onClick={() => handleSave(false)}
                disabled={!selectedPoster}
              >
                Save
              </button>
              {canUpload && (
                <button
                  className={`${styles.footerButton} ${defaultUpload ? styles.save : styles.secondary}`}
                  onClick={() => handleSave(true)}
                  disabled={!selectedPoster}
                >
                  Save &amp; upload
                </button>
              )}
            </>
          )}
        </div>
      </Modal>
    </>
  );
}
