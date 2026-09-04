import { useEffect, useEffectEvent, useState } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';

import { errorMessage, styleProfilesApi } from '../../api';
import { ConfirmModal } from '../common';
import { StyleProfileModal } from './StyleProfileModal';
import { useToast } from '../../context/ToastContext';
import type { StyleProfile } from '../../types';
import { profileDeleteMessage } from './libraryStyle';
import sectionStyles from './SettingsSection.module.css';
import styles from './StyleProfilesPanel.module.css';

export function StyleProfilesPanel() {
  const toast = useToast();
  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editTarget, setEditTarget] = useState<StyleProfile | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<StyleProfile | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  const load = useEffectEvent(async () => {
    try {
      setProfiles(await styleProfilesApi.getProfiles());
    } catch (err) {
      toast.error(errorMessage(err, 'Could not load the style profiles.'), {
        title: 'Style profiles',
      });
    } finally {
      setIsLoading(false);
    }
  });

  useEffect(() => {
    void load();
  }, []);

  const handleSaved = (saved: StyleProfile) => {
    setProfiles((prev) =>
      prev.some((p) => p.id === saved.id)
        ? prev.map((p) => (p.id === saved.id ? saved : p))
        : [...prev, saved]
    );
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await styleProfilesApi.deleteProfile(deleteTarget.id);
      setProfiles((prev) => prev.filter((p) => p.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete the profile.'), { title: 'Style profiles' });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h2 className={sectionStyles.sectionTitle}>Style Profiles</h2>
          <p className={sectionStyles.sectionDescription}>
            Named styles shared across libraries. A library picks one in its Poster Style editor,
            and every library using a profile follows it.
          </p>
        </div>
        <button className={sectionStyles.saveButton} onClick={() => setIsCreating(true)}>
          <Plus size={16} />
          New profile
        </button>
      </div>

      {isLoading ? (
        <div className={sectionStyles.emptyState}>Loading style profiles…</div>
      ) : profiles.length === 0 ? (
        <div className={sectionStyles.emptyState}>
          No style profiles yet. Create one here, or save a library's custom style as one.
        </div>
      ) : (
        <ul className={styles.list}>
          {profiles.map((profile) => (
            <li key={profile.id} className={styles.row}>
              <span className={styles.name}>{profile.name}</span>
              <span className={styles.usage}>
                {profile.library_count === 1 ? '1 library' : `${profile.library_count} libraries`}
              </span>
              <button
                className={styles.iconButton}
                aria-label={`Edit ${profile.name}`}
                onClick={() => setEditTarget(profile)}
              >
                <Pencil size={15} />
              </button>
              <button
                className={`${styles.iconButton} ${styles.danger}`}
                aria-label={`Delete ${profile.name}`}
                onClick={() => setDeleteTarget(profile)}
              >
                <Trash2 size={15} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {isCreating && (
        <StyleProfileModal onSaved={handleSaved} onClose={() => setIsCreating(false)} />
      )}

      {editTarget && (
        <StyleProfileModal
          profile={editTarget}
          onSaved={handleSaved}
          onClose={() => setEditTarget(null)}
        />
      )}

      {deleteTarget && (
        <ConfirmModal
          title="Delete style profile"
          message={profileDeleteMessage(deleteTarget)}
          confirmLabel={isDeleting ? 'Deleting…' : 'Delete'}
          variant="danger"
          isBusy={isDeleting}
          onConfirm={handleConfirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
