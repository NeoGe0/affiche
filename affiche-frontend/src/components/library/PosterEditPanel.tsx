import { RotateCcw, Loader2 } from 'lucide-react';
import { PosterPreview, PosterStyleControls } from '../image';
import { useFonts } from '../../hooks';
import { POSTER_LANGUAGES } from '../../constants/languages';
import type { OverlayOptions, TextOptions } from '../../types';
import styles from './PosterEditPanel.module.css';

interface PosterEditPanelProps {

  imageUrl: string | null;
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
    <section className={styles.editor} aria-labelledby="poster-style-heading">
      <div className={styles.header}>
        <h3 className={styles.headerTitle} id="poster-style-heading">Edit style</h3>
        <button className={styles.resetButton} onClick={onReset}>
          <RotateCcw size={14} />
          Reset to defaults
        </button>
        <button className={styles.doneButton} onClick={onClose}>
          Done
        </button>
      </div>

      <div className={styles.previewRow}>
        <div className={styles.previewWrapper}>
          {imageUrl ? (
            <PosterPreview
              imageUrl={imageUrl}
              title={title}
              overlayOptions={overlayOptions}
              textOptions={textOptions}
            />
          ) : (
            <div className={styles.previewPlaceholder}>No poster selected</div>
          )}
        </div>
        <p className={styles.previewNote}>
          Pick any poster in the grid: it takes this style straight away.
        </p>
      </div>

      <div className={styles.content}>

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

    </section>
  );
}
