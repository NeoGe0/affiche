import { useState, useEffect, useEffectEvent, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Upload, Trash2, Check, Loader, Save, ArrowLeft, Clapperboard, X } from 'lucide-react';
import { errorMessage, settingsApi, fontsApi } from '../../api';
import { useToast } from '../../context/ToastContext';
import { useFonts, invalidatePosterConfig, usePreviewSubject } from '../../hooks';
import { PosterPreview, PosterStyleControls, fontBaseName } from '../image';
import { ConfirmModal } from '../common';
import { PreviewSubjectModal } from './PreviewSubjectModal';
import { StyleProfilesPanel } from './StyleProfilesPanel';
import type { OverlayOptions, TextOptions, GenerationOptions, PosterConfig } from '../../types';
import { TEXTLESS } from '../../constants/languages';
import samplePoster from '../../assets/sample-poster.svg';
import sectionStyles from './SettingsSection.module.css';
import styles from './StyleSettings.module.css';

const SAMPLE_TITLE = 'Sample Title';

type StyleSection = 'main' | 'fonts' | 'profiles';

export function StyleSettings() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const sectionParam = searchParams.get('section');
  const section: StyleSection =
    sectionParam === 'fonts' || sectionParam === 'profiles' ? sectionParam : 'main';

  const { fonts, reload: reloadFonts } = useFonts();

  const [overlay, setOverlay] = useState<OverlayOptions | null>(null);
  const [text, setText] = useState<TextOptions | null>(null);
  const [gen, setGen] = useState<GenerationOptions | null>(null);
  const [saved, setSaved] = useState<PosterConfig | null>(null);
  const [userFonts, setUserFonts] = useState<string[]>([]);

  const [isSaving, setIsSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState(false);

  const [loadFailed, setLoadFailed] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [settingDefault, setSettingDefault] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPickingSubject, setIsPickingSubject] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const preview = usePreviewSubject(TEXTLESS);

  const load = useEffectEvent(async () => {
    try {
      const cfg = await settingsApi.getPosterConfig();
      setOverlay(cfg.overlay_options);
      setText(cfg.text_options);
      setGen(cfg.generation_options);
      setSaved(cfg);
    } catch (err) {
      setLoadFailed(true);
      toast.error(errorMessage(err, 'Failed to load the style options.'), {
        title: 'Style options',
      });
    }

    try {
      setUserFonts(await fontsApi.getUserFonts());
    } catch {
      setUserFonts([]);
    }
  });

  useEffect(() => {
    void load();
  }, []);

  const goToSection = (next: StyleSection) => {
    const params = new URLSearchParams(searchParams);
    params.set('tab', 'style');
    if (next === 'main') params.delete('section');
    else params.set('section', next);
    setSearchParams(params);
  };

  const updateOverlay = (changes: Partial<OverlayOptions>) => {
    setOverlay((prev) => (prev ? { ...prev, ...changes } : prev));
    setSavedMsg(false);
  };
  const updateText = (changes: Partial<TextOptions>) => {
    setText((prev) => (prev ? { ...prev, ...changes } : prev));
    setSavedMsg(false);
  };
  const updateGen = (changes: Partial<GenerationOptions>) => {
    setGen((prev) => (prev ? { ...prev, ...changes } : prev));
    setSavedMsg(false);
  };

  const setDefaultFont = async (name: string) => {
    if (!saved) return;
    setSettingDefault(name);
    try {
      const updated = await settingsApi.updatePosterConfig({
        overlay_options: saved.overlay_options,
        text_options: { ...saved.text_options, font_name: name },
        generation_options: saved.generation_options,
      });
      setSaved(updated);

      invalidatePosterConfig();
      updateText({ font_name: name });
    } catch (err) {
      toast.error(errorMessage(err, 'Could not set the default font.'), { title: 'Fonts' });
    } finally {
      setSettingDefault(null);
    }
  };

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    setIsUploading(true);
    try {
      await fontsApi.uploadFont(file);
      await reloadFonts();
      setUserFonts(await fontsApi.getUserFonts());
    } catch (err) {
      toast.error(errorMessage(err, 'Could not upload the font.'), { title: 'Font upload' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await fontsApi.deleteFont(deleteTarget);
      const remaining = await reloadFonts();
      setUserFonts(await fontsApi.getUserFonts());

      if (saved && saved.text_options.font_name === deleteTarget && remaining.length > 0) {
        await setDefaultFont(remaining[0]);
      }
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete the font.'), { title: 'Fonts' });
    } finally {
      setIsDeleting(false);
      setDeleteTarget(null);
    }
  };

  const handleSave = async () => {
    if (!overlay || !text || !gen) return;
    setIsSaving(true);
    try {
      const updated = await settingsApi.updatePosterConfig({
        overlay_options: overlay,
        text_options: text,
        generation_options: gen,
      });
      setOverlay(updated.overlay_options);
      setText(updated.text_options);
      setGen(updated.generation_options);
      setSaved(updated);
      invalidatePosterConfig();
      setSavedMsg(true);
    } catch (err) {
      toast.error(errorMessage(err, 'Could not save the style defaults.'), {
        title: 'Style options',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (saved) {
      setOverlay(saved.overlay_options);
      setText(saved.text_options);
      setGen(saved.generation_options);
      setSavedMsg(false);
    }
  };

  if (section === 'profiles') {
    return (
      <section className={sectionStyles.section}>
        <button className={styles.backLink} onClick={() => goToSection('main')}>
          <ArrowLeft size={16} />
          Style Options
        </button>

        <StyleProfilesPanel />
      </section>
    );
  }

  if (!overlay || !text || !gen) {
    return (
      <section className={sectionStyles.section}>
        <h2 className={sectionStyles.sectionTitle}>Style Options</h2>
        <div className={sectionStyles.emptyState}>
          {loadFailed ? 'Could not load the style options.' : 'Loading style options…'}
        </div>
      </section>
    );
  }

  if (section === 'fonts') {
    return (
      <section className={sectionStyles.section}>
        <button className={styles.backLink} onClick={() => goToSection('main')}>
          <ArrowLeft size={16} />
          Style Options
        </button>

        <div className={sectionStyles.sectionHeader}>
          <div>
            <h2 className={sectionStyles.sectionTitle}>Fonts</h2>
            <p className={sectionStyles.sectionDescription}>
              Preview available fonts, upload your own, and choose the default used for generation.
            </p>
          </div>
          <button className={sectionStyles.saveButton} onClick={handleUploadClick} disabled={isUploading}>
            {isUploading ? <Loader size={16} className={styles.spinning} /> : <Upload size={16} />}
            {isUploading ? 'Uploading…' : 'Upload font'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".ttf,.otf"
            className={styles.hiddenFileInput}
            onChange={handleFileSelected}
          />
        </div>

        <div className={styles.fontGrid}>
          {fonts.map((font) => {
            const isDefault = text.font_name === font;
            const isUser = userFonts.includes(font);
            const isBusy = settingDefault === font;
            return (
              <div key={font} className={`${styles.fontCard} ${isDefault ? styles.default : ''}`}>
                <div className={styles.fontSample} style={{ fontFamily: `"${fontBaseName(font)}"` }}>
                  {SAMPLE_TITLE}
                </div>
                <div className={styles.fontName}>{fontBaseName(font)}</div>
                <div className={styles.fontActions}>
                  {isDefault ? (
                    <span className={styles.defaultBadge}>
                      <Check size={13} /> Default
                    </span>
                  ) : (
                    <button
                      className={styles.setDefaultButton}
                      onClick={() => setDefaultFont(font)}
                      disabled={isBusy}
                    >
                      {isBusy ? 'Setting…' : 'Set as default'}
                    </button>
                  )}
                  {isUser && (
                    <button
                      className={styles.deleteButton}
                      title="Delete font"
                      onClick={() => setDeleteTarget(font)}
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {deleteTarget && (
          <ConfirmModal
            title="Delete font"
            message={`Delete "${fontBaseName(deleteTarget)}"? This removes the uploaded font file.`}
            confirmLabel={isDeleting ? 'Deleting…' : 'Delete'}
            variant="danger"

            isBusy={isDeleting}
            onConfirm={handleConfirmDelete}
            onCancel={() => setDeleteTarget(null)}
          />
        )}
      </section>
    );
  }

  const isDirty =
    !saved ||
    JSON.stringify(saved.overlay_options) !== JSON.stringify(overlay) ||
    JSON.stringify(saved.text_options) !== JSON.stringify(text) ||
    JSON.stringify(saved.generation_options) !== JSON.stringify(gen);

  return (
    <section className={sectionStyles.section}>
      <h2 className={sectionStyles.sectionTitle}>Style Options</h2>
      {
}
      <p className={sectionStyles.sectionDescription}>
        Default styling applied when generating posters. Every library follows these unless it sets
        a style of its own.
      </p>

      <h3 className={styles.subTitle}>Generation Defaults</h3>
      <p className={styles.subDescription}>
        These defaults are applied to every poster during generation.
      </p>

      <div className={styles.editor}>
        <div className={styles.previewColumn}>
          <div className={styles.previewWrapper}>
            <PosterPreview
              imageUrl={preview.artworkUrl ?? samplePoster}
              title={preview.subject?.title ?? SAMPLE_TITLE}
              overlayOptions={overlay}
              textOptions={text}
            />
          </div>

          <div className={styles.previewSubject}>
            <button className={styles.subjectButton} onClick={() => setIsPickingSubject(true)}>
              <Clapperboard size={15} />
              {preview.subject ? preview.subject.title : 'Choose a title…'}
            </button>
            {preview.subject && (
              <button
                className={styles.subjectClear}
                title="Back to the sample poster"
                aria-label="Back to the sample poster"
                onClick={preview.clear}
              >
                <X size={15} />
              </button>
            )}
          </div>

          {
}
          {preview.isLoading && <p className={styles.subjectNote}>Fetching artwork…</p>}
          {preview.error && <p className={styles.errorMsg}>{preview.error}</p>}
        </div>

        <div className={styles.controls}>
          <PosterStyleControls
            overlayOptions={overlay}
            textOptions={text}
            jpegQuality={gen.jpeg_quality}
            onOverlayChange={updateOverlay}
            onTextChange={updateText}
            onQualityChange={(jpeg_quality) => updateGen({ jpeg_quality })}
            fonts={fonts}
          />

          <div className={styles.footer}>
            <button className={sectionStyles.saveButton} onClick={handleSave} disabled={isSaving || !isDirty}>
              {isSaving ? <Loader size={16} className={styles.spinning} /> : <Save size={16} />}
              {isSaving ? 'Saving…' : 'Save Defaults'}
            </button>
            <button className={styles.setDefaultButton} onClick={handleReset} disabled={!isDirty || isSaving}>
              Reset
            </button>
            {savedMsg && <span className={styles.savedMsg}>Saved</span>}
          </div>
        </div>
      </div>

      {isPickingSubject && (
        <PreviewSubjectModal
          onClose={() => setIsPickingSubject(false)}
          onSelect={preview.choose}
        />
      )}
    </section>
  );
}
