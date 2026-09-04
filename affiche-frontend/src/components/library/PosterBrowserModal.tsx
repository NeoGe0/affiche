import { useState } from 'react';
import { Loader2 } from 'lucide-react';

import { Modal } from '../common';
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
import type { OverlayOptions, TextOptions } from '../../types';
import styles from './PosterBrowserModal.module.css';

interface PosterBrowserModalProps {

  target: PosterTarget;

  seasonNumber?: number;
  onClose: () => void;
  onSave: (
    posterUrl: string,
    opts: { overlayOptions?: OverlayOptions; textOptions?: TextOptions; jpegQuality?: number; title?: string; upload?: boolean }
  ) => void;
  isSaving?: boolean;

  defaultUpload?: boolean;

  canUpload?: boolean;
}

export function PosterBrowserModal({
  target,
  seasonNumber,
  onClose,
  onSave,
  isSaving = false,
  defaultUpload = false,
  canUpload = true,
}: PosterBrowserModalProps) {
  const { config: posterConfig } = usePosterConfig();
  const { isAnyProviderConfigured, configuredProviders } = useProviderStatus();

  const { title: itemTitle, year, mediaType, tmdbId, tvdbId, collectionId } = target;
  const isSeason = seasonNumber !== undefined;
  const defaultTitle = isSeason ? `Season ${seasonNumber}` : itemTitle;

  const [selectedPoster, setSelectedPoster] = useState<string | null>(null);
  const [showEditPanel, setShowEditPanel] = useState(false);
  const [uploadToLibrary, setUploadToLibrary] = useState(defaultUpload);

  const query = usePosterBrowseQuery({
    itemTitle,
    year,
    seasonNumber,
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

  const stageCustom = async (params: { file?: File; url?: string }) => {
    const staged = await candidates.stageCustom(params);

    if (staged) setSelectedPoster(staged);
  };

  const titleLanguageEnabled = isAnyProviderConfigured && (tmdbId !== undefined || tvdbId !== undefined);

  const handleSave = () => {
    if (!selectedPoster) return;
    onSave(selectedPoster, {
      overlayOptions,
      textOptions,
      jpegQuality: quality,
      title: titleDraft.title,
      upload: uploadToLibrary,
    });
  };

  const modalTitle = isSeason
    ? `Select Poster for "${itemTitle}" - Season ${seasonNumber}`
    : `Select Poster for "${itemTitle}"`;

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
            seasonSource={
              isSeason
                ? {
                    seasonNumber: query.searchSeasonNumber,
                    onSeasonNumberChange: query.changeSearchSeasonNumber,
                    useShowArt: query.useShowArt,
                    onUseShowArtChange: query.changeUseShowArt,
                    appliesToSeason: seasonNumber,
                  }
                : undefined
            }
          />

          <div className={styles.mainArea}>
            <PosterCandidateGrid
              posters={sortPosterCandidates(candidates.posters, query.sort)}
              selected={selectedPoster}
              isLoading={candidates.isLoading}
              onSelect={setSelectedPoster}
            />

            {!showEditPanel && (
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
          {canUpload && (
            <label className={styles.uploadToggle}>
              <input
                type="checkbox"
                checked={uploadToLibrary}
                onChange={(e) => setUploadToLibrary(e.target.checked)}
              />
              <span>Upload to library</span>
            </label>
          )}
          <button
            className={`${styles.footerButton} ${styles.cancel}`}
            onClick={onClose}
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            className={`${styles.footerButton} ${styles.save}`}
            onClick={handleSave}
            disabled={!selectedPoster || isSaving}
          >
            {isSaving ? (
              <>
                <Loader2 size={16} className="spin" />
                Saving...
              </>
            ) : (
              'Save'
            )}
          </button>
        </div>
      </Modal>

      {}
      {showEditPanel && selectedPoster && overlayOptions && textOptions && (
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
          onReset={style.reset}
          onClose={() => setShowEditPanel(false)}
        />
      )}
    </>
  );
}
