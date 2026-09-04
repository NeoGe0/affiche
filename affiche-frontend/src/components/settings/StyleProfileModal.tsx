import { useId, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

import { errorMessage, styleProfilesApi } from '../../api';
import { Modal } from '../common';
import { PosterPreview, PosterStyleControls } from '../image';
import { useFonts, usePosterConfig } from '../../hooks';
import { useToast } from '../../context/ToastContext';
import type { OverlayOptions, PosterConfig, StyleProfile, TextOptions } from '../../types';
import { profileEditWarning, type LibraryStyle } from './libraryStyle';
import samplePoster from '../../assets/sample-poster.svg';
import sectionStyles from './SettingsSection.module.css';
import styles from './StyleProfileModal.module.css';

const SAMPLE_TITLE = 'Sample Title';

interface StyleProfileModalProps {

  profile?: StyleProfile;
  onSaved: (profile: StyleProfile) => void;
  onClose: () => void;
}

function seedStyle(config: PosterConfig, profile?: StyleProfile): LibraryStyle {
  return {
    overlay: { ...config.overlay_options, ...(profile?.overlay_options as Partial<OverlayOptions>) },
    text: { ...config.text_options, ...(profile?.text_options as Partial<TextOptions>) },
  };
}

export function StyleProfileModal({ profile, onSaved, onClose }: StyleProfileModalProps) {
  const toast = useToast();
  const uid = useId();
  const { fonts } = useFonts();
  const { config, isLoading, error } = usePosterConfig();

  const [name, setName] = useState(profile?.name ?? '');
  const [draft, setDraft] = useState<LibraryStyle | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const isEdit = profile !== undefined;
  const style = draft ?? (config ? seedStyle(config, profile) : null);
  const editWarning = profile ? profileEditWarning(profile) : null;

  const updateOverlay = (changes: Partial<OverlayOptions>) => {
    if (style) setDraft({ ...style, overlay: { ...style.overlay, ...changes } });
  };
  const updateText = (changes: Partial<TextOptions>) => {
    if (style) setDraft({ ...style, text: { ...style.text, ...changes } });
  };

  const handleSave = async () => {
    if (!style || !name.trim()) return;
    setIsSaving(true);
    try {
      const payload = {
        name: name.trim(),
        overlay_options: { ...style.overlay },
        text_options: { ...style.text },
      };
      const saved = profile
        ? await styleProfilesApi.updateProfile(profile.id, payload)
        : await styleProfilesApi.createProfile(payload);
      onSaved(saved);
      onClose();
    } catch (err) {

      toast.error(
        errorMessage(err, `Could not ${isEdit ? 'save' : 'create'} the style profile.`),
        { title: 'Style profiles' }
      );
    } finally {
      setIsSaving(false);
    }
  };

  const heading = isEdit ? `Edit ${profile.name}` : 'New style profile';

  const footer = (
    <>
      <button className={sectionStyles.outlineButton} onClick={onClose} disabled={isSaving}>
        Cancel
      </button>
      <button
        className={sectionStyles.saveButton}
        onClick={handleSave}
        disabled={isSaving || !style || !name.trim()}
      >
        {isSaving
          ? isEdit ? 'Saving…' : 'Creating…'
          : isEdit ? 'Save profile' : 'Create profile'}
      </button>
    </>
  );

  return (
    <Modal
      size="large"
      label={heading}
      title={heading}
      description={'A named style any library can be pointed at. It starts from the global style '
        + 'options — adjust what should differ, and every library using the profile follows it.'}
      isBusy={isSaving}
      onClose={onClose}
      footer={footer}
    >
      <div className={styles.body}>
        {editWarning && (
          <p className={styles.warning}>
            <AlertTriangle size={15} aria-hidden="true" />
            <span>{editWarning}</span>
          </p>
        )}

        <label className={styles.nameField} htmlFor={`${uid}-name`}>
          <span className={styles.nameLabel}>Name</span>
          <input
            id={`${uid}-name`}
            type="text"
            className={styles.nameInput}
            placeholder="e.g. Anime"
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>

        {!style ? (
          <p className={sectionStyles.emptyState}>
            {error || !isLoading
              ? 'Could not load the global style to start from.'
              : 'Loading the style options…'}
          </p>
        ) : (
          <div className={styles.editor}>
            <div className={styles.previewColumn}>
              <PosterPreview
                imageUrl={samplePoster}
                title={SAMPLE_TITLE}
                overlayOptions={style.overlay}
                textOptions={style.text}
              />
            </div>
            <div className={styles.controlsColumn}>
              <PosterStyleControls
                overlayOptions={style.overlay}
                textOptions={style.text}
                onOverlayChange={updateOverlay}
                onTextChange={updateText}
                fonts={fonts}
              />
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
