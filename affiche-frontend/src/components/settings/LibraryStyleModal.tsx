import { useEffect, useEffectEvent, useId, useState } from 'react';
import { AlertTriangle, Save } from 'lucide-react';

import { errorMessage, libraryApi, styleProfilesApi } from '../../api';
import { Modal } from '../common';
import { PosterPreview, PosterStyleControls } from '../image';
import { useFonts, usePosterConfig } from '../../hooks';
import { useToast } from '../../context/ToastContext';
import type {
  LibrarySettings,
  LibraryStyleStaleness,
  OverlayOptions,
  StyleProfile,
  TextOptions,
} from '../../types';
import {
  customStylePatch,
  INHERIT_STYLE,
  profileStylePatch,
  resolveLibraryStyle,
  stalenessMessage,
  styleModeOf,
  type LibraryStyle,
  type StyleMode,
} from './libraryStyle';
import samplePoster from '../../assets/sample-poster.svg';
import sectionStyles from './SettingsSection.module.css';
import styles from './LibraryStyleModal.module.css';

const SAMPLE_TITLE = 'Sample Title';

interface LibraryStyleModalProps {
  libraryName: string;
  mediaServerId: number;
  libraryId: number;
  settings: LibrarySettings;
  onApply: (patch: Partial<LibrarySettings>) => void;
  onClose: () => void;
}

export function LibraryStyleModal({
  libraryName,
  mediaServerId,
  libraryId,
  settings,
  onApply,
  onClose,
}: LibraryStyleModalProps) {
  const toast = useToast();
  const uid = useId();
  const { fonts } = useFonts();
  const { config, isLoading, error } = usePosterConfig();

  const [staleness, setStaleness] = useState<LibraryStyleStaleness | null>(null);

  const loadStaleness = useEffectEvent(async () => {
    try {
      setStaleness(await libraryApi.getStyleStaleness(mediaServerId, libraryId));
    } catch {
      setStaleness(null);
    }
  });

  useEffect(() => {
    void loadStaleness();
  }, []);

  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const loadProfiles = useEffectEvent(async () => {
    try {
      setProfiles(await styleProfilesApi.getProfiles());
    } catch {
      setProfiles([]);
    }
  });

  useEffect(() => {
    void loadStaleness();
    void loadProfiles();
  }, []);

  const [mode, setMode] = useState<StyleMode>(styleModeOf(settings));
  const [profileId, setProfileId] = useState<number | null>(settings.style_profile_id ?? null);

  const [draft, setDraft] = useState<LibraryStyle | null>(null);
  const [newProfileName, setNewProfileName] = useState('');
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  const style = draft ?? (config ? resolveLibraryStyle(settings, config, profiles) : null);
  const staleMessage = stalenessMessage(staleness);

  const updateOverlay = (changes: Partial<OverlayOptions>) => {
    if (style) setDraft({ ...style, overlay: { ...style.overlay, ...changes } });
  };
  const updateText = (changes: Partial<TextOptions>) => {
    if (style) setDraft({ ...style, text: { ...style.text, ...changes } });
  };

  const handleSaveAsProfile = async () => {
    if (!style || !newProfileName.trim()) return;
    setIsSavingProfile(true);
    try {
      const created = await styleProfilesApi.createProfile({
        name: newProfileName.trim(),
        overlay_options: { ...style.overlay },
        text_options: { ...style.text },
      });
      setProfiles((prev) => [...prev, created]);
      setNewProfileName('');
      setProfileId(created.id);
      setMode('profile');
    } catch (err) {
      toast.error(errorMessage(err, 'Could not save the style profile.'), {
        title: 'Style profiles',
      });
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleApply = () => {
    if (mode === 'global') {
      onApply(INHERIT_STYLE);
    } else if (mode === 'profile') {
      if (profileId == null) return;
      onApply(profileStylePatch(profileId));
    } else {
      if (!style) return;
      onApply(customStylePatch(style));
    }
    onClose();
  };

  const canApply =
    mode === 'global' || (mode === 'profile' ? profileId != null : Boolean(style));

  const footer = (
    <>
      <button className={sectionStyles.outlineButton} onClick={onClose}>
        Cancel
      </button>
      <button className={sectionStyles.saveButton} onClick={handleApply} disabled={!canApply}>
        Apply
      </button>
    </>
  );

  return (
    <Modal
      size="large"
      label={`Poster style for ${libraryName}`}
      title="Poster style"
      description={
        <>
          What <strong>{libraryName}</strong> generates with. Applies on the card&rsquo;s Save, and
          takes effect the next time posters are generated — existing posters keep the style they
          were made with.
        </>
      }
      onClose={onClose}
      footer={footer}
    >
      <div className={styles.body}>
        {staleMessage && (
          <p className={styles.staleness}>
            <AlertTriangle size={15} aria-hidden="true" />
            <span>
              {staleMessage} Regenerate them to pick up the current one.
            </span>
          </p>
        )}
        <fieldset className={styles.modeGroup}>
          <legend className={styles.modeLegend}>Style source</legend>
          <label className={styles.mode}>
            <input
              type="radio"
              name="library-style-mode"
              checked={mode === 'global'}
              onChange={() => setMode('global')}
            />
            <span>
              <span className={styles.modeName}>Global style</span>
              <span className={sectionStyles.settingDescription}>
                Follow Settings → Style Options, including later changes to it.
              </span>
            </span>
          </label>
          <label className={styles.mode}>
            <input
              type="radio"
              name="library-style-mode"
              checked={mode === 'profile'}
              disabled={profiles.length === 0}
              onChange={() => setMode('profile')}
            />
            <span>
              <span className={styles.modeName}>Style profile</span>
              <span className={sectionStyles.settingDescription}>
                {profiles.length === 0
                  ? 'No profiles yet — build a custom style below and save it as one.'
                  : 'A named style shared with other libraries. Editing it restyles them all.'}
              </span>
            </span>
          </label>
          {mode === 'profile' && (
            <label className={styles.profilePicker}>
              <span className={styles.profileLabel}>Profile</span>
              <select
                className={styles.profileSelect}
                value={profileId ?? ''}
                onChange={(e) => setProfileId(Number(e.target.value))}
              >
                <option value="" disabled>
                  Choose a profile…
                </option>
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className={styles.mode}>
            <input
              type="radio"
              name="library-style-mode"
              checked={mode === 'custom'}
              onChange={() => setMode('custom')}
            />
            <span>
              <span className={styles.modeName}>Custom style</span>
              <span className={sectionStyles.settingDescription}>
                Override the defaults for this library only.
              </span>
            </span>
          </label>
        </fieldset>

        {mode === 'custom' && !style && (
          <p className={sectionStyles.emptyState}>
            {error || !isLoading
              ? 'Could not load the global style to start from.'
              : 'Loading the style options…'}
          </p>
        )}

        {mode === 'custom' && style && (
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

              <div className={styles.saveAsProfile}>
                <label className={styles.profileLabel} htmlFor={`${uid}-profile-name`}>
                  Save as a profile
                </label>
                <p className={sectionStyles.settingDescription}>
                  Give this style a name to reuse it on other libraries.
                </p>
                <div className={styles.saveAsRow}>
                  <input
                    id={`${uid}-profile-name`}
                    type="text"
                    className={styles.profileNameInput}
                    placeholder="e.g. Anime"
                    value={newProfileName}
                    onChange={(e) => setNewProfileName(e.target.value)}
                  />
                  <button
                    className={sectionStyles.outlineButton}
                    onClick={handleSaveAsProfile}
                    disabled={isSavingProfile || !newProfileName.trim()}
                  >
                    <Save size={14} />
                    {isSavingProfile ? 'Saving…' : 'Save profile'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
