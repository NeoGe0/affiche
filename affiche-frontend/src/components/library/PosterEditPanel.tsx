import { ArrowLeft, RotateCcw, Loader2 } from 'lucide-react';
import { Modal } from '../common';
import { PosterPreview, PosterStyleControls } from '../image';
import { useFonts } from '../../hooks';
import { POSTER_LANGUAGES } from '../../constants/languages';
import type { OverlayOptions, TextOptions } from '../../types';
import styles from './PosterEditPanel.module.css';

interface PosterEditPanelProps {
  imageUrl: string;
  title: string;
  onTitleChange: (title: string) => void;
  titleLanguage: string;
  onTitleLanguageChange: (language: string) => void;
  titleLanguageEnabled: boolean;
  isTranslating: boolean;
  titleNotFound: boolean;
  overlayOptions: OverlayOptions;
  textOptions: TextOptions;
  jpegQuality: number;
  onOverlayChange: (options: Partial<OverlayOptions>) => void;
  onTextChange: (options: Partial<TextOptions>) => void;
  onQualityChange: (quality: number) => void;
  onReset: () => void;
  onClose: () => void;
}

export function PosterEditPanel({
  imageUrl,
  title,
  onTitleChange,
  titleLanguage,
  onTitleLanguageChange,
  titleLanguageEnabled,
  isTranslating,
  titleNotFound,
  overlayOptions,
  textOptions,
  jpegQuality,
  onOverlayChange,
  onTextChange,
  onQualityChange,
  onReset,
  onClose,
}: PosterEditPanelProps) {
  const { fonts } = useFonts();

  return (

    <Modal size="large" label="Edit poster style" elevated onClose={onClose}>
      <div className={styles.header}>
        <button className={styles.backButton} onClick={onClose}>
          <ArrowLeft size={20} />
          <span>Back to Selection</span>
        </button>
        <h3 className={styles.headerTitle}>Edit Poster Style</h3>
      </div>

      <div className={styles.content}>
        <div className={styles.previewWrapper}>
          <PosterPreview
            imageUrl={imageUrl}
            title={title}
            overlayOptions={overlayOptions}
            textOptions={textOptions}
          />
        </div>

        <PosterStyleControls
          overlayOptions={overlayOptions}
          textOptions={textOptions}
          jpegQuality={jpegQuality}
          onOverlayChange={onOverlayChange}
          onTextChange={onTextChange}
          onQualityChange={onQualityChange}
          fonts={fonts}

          titleSlot={
            <>
              {

}
              <div className={styles.row}>
                <label className={styles.label} htmlFor="poster-title">Title</label>
                <textarea
                  id="poster-title"
                  rows={2}
                  className={styles.textArea}
                  value={title}
                  onChange={(e) => onTitleChange(e.target.value)}
                />
              </div>

              <div className={styles.row}>
                <span className={styles.hint}>Press Enter to break the title onto a new line.</span>
              </div>

              <div className={styles.row}>
                <label className={styles.label} htmlFor="poster-title-language">Title language</label>
                <div className={styles.selectWithStatus}>
                  <select
                    id="poster-title-language"
                    className={styles.select}
                    value={titleLanguage}
                    onChange={(e) => onTitleLanguageChange(e.target.value)}
                    disabled={!titleLanguageEnabled || isTranslating}
                    title={
                      titleLanguageEnabled
                        ? undefined
                        : 'Configure a poster provider (and matching TMDB/TVDB id) to look up localized names'
                    }
                  >
                    <option value="">Original</option>
                    {POSTER_LANGUAGES.map((lang) => (
                      <option key={lang.value} value={lang.value}>
                        {lang.label}
                      </option>
                    ))}
                  </select>
                  {isTranslating && <Loader2 size={14} className="spin" />}
                </div>
              </div>

              {titleNotFound && (
                <div className={styles.row}>
                  <span className={styles.hint}>
                    No localized name found; keeping the current title.
                  </span>
                </div>
              )}
            </>
          }
        />
      </div>

      <div className={styles.footer}>
        <button className={styles.resetButton} onClick={onReset}>
          <RotateCcw size={16} />
          Reset to Defaults
        </button>
        <button className={styles.doneButton} onClick={onClose}>
          Done
        </button>
      </div>
    </Modal>
  );
}
