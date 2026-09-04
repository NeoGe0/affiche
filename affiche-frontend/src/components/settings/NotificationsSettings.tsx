import { useEffect, useEffectEvent, useState } from 'react';
import { Pencil, Plus, Send, Trash2 } from 'lucide-react';

import { errorMessage, notificationsApi } from '../../api';
import { ConfirmModal } from '../common';
import { NotificationTargetModal } from './NotificationTargetModal';
import { useToast } from '../../context/ToastContext';
import type { NotificationTarget } from '../../types';
import { notificationTypeLabel, subscribedEvents } from './notificationTarget';
import sectionStyles from './SettingsSection.module.css';
import styles from './NotificationsSettings.module.css';

export function NotificationsSettings() {
  const toast = useToast();
  const [targets, setTargets] = useState<NotificationTarget[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [editTarget, setEditTarget] = useState<NotificationTarget | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<NotificationTarget | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  const load = useEffectEvent(async () => {
    try {
      setTargets(await notificationsApi.getTargets());
    } catch (err) {
      toast.error(errorMessage(err, 'Could not load the notification targets.'), {
        title: 'Notifications',
      });
    } finally {
      setIsLoading(false);
    }
  });

  useEffect(() => {
    void load();
  }, []);

  const handleSaved = (saved: NotificationTarget) => {
    setTargets((prev) =>
      prev.some((t) => t.id === saved.id)
        ? prev.map((t) => (t.id === saved.id ? saved : t))
        : [...prev, saved]
    );
  };

  const handleToggle = async (target: NotificationTarget) => {
    try {
      handleSaved(await notificationsApi.updateTarget(target.id, { enabled: !target.enabled }));
    } catch (err) {
      toast.error(errorMessage(err, 'Could not change the target.'), { title: 'Notifications' });
    }
  };

  const handleTest = async (target: NotificationTarget) => {
    setTestingId(target.id);
    try {
      const { delivered } = await notificationsApi.testTarget(target.id);
      if (delivered) {
        toast.success(`${target.name} accepted the test message.`, { title: 'Notifications' });
      } else {

        toast.error(`${target.name} did not accept the message. Check its URL.`, {
          title: 'Notifications',
        });
      }
    } catch (err) {
      toast.error(errorMessage(err, 'Could not send the test.'), { title: 'Notifications' });
    } finally {
      setTestingId(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await notificationsApi.deleteTarget(deleteTarget.id);
      setTargets((prev) => prev.filter((t) => t.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete the target.'), { title: 'Notifications' });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <section className={sectionStyles.section}>
      <div className={sectionStyles.sectionHeader}>
        <div>
          <h2 className={sectionStyles.sectionTitle}>Notifications</h2>
          <p className={sectionStyles.sectionDescription}>
            Affiche can tell you when a background run ends, so a scheduled pickup that failed does
            not wait for you to open the app. Each target chooses which events it hears about.
          </p>
        </div>
        <button className={sectionStyles.saveButton} onClick={() => setIsCreating(true)}>
          <Plus size={16} />
          New target
        </button>
      </div>

      {isLoading ? (
        <div className={sectionStyles.emptyState}>Loading notification targets…</div>
      ) : targets.length === 0 ? (
        <div className={sectionStyles.emptyState}>
          No notification targets yet. Add a Discord, Gotify or Apprise URL — or any endpoint that
          accepts a POST — to hear about finished runs.
        </div>
      ) : (
        <ul className={styles.list}>
          {targets.map((target) => (
            <li key={target.id} className={styles.row}>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={target.enabled}
                  onChange={() => handleToggle(target)}
                  aria-label={`Enable ${target.name}`}
                />
              </label>
              <span className={styles.name}>{target.name}</span>
              <span className={styles.meta}>
                {notificationTypeLabel(target.type)} · {target.url_hint}
              </span>
              <span className={styles.events}>on {subscribedEvents(target)}</span>
              <button
                className={styles.iconButton}
                aria-label={`Send a test to ${target.name}`}
                disabled={testingId === target.id}
                onClick={() => handleTest(target)}
              >
                <Send size={15} />
              </button>
              <button
                className={styles.iconButton}
                aria-label={`Edit ${target.name}`}
                onClick={() => setEditTarget(target)}
              >
                <Pencil size={15} />
              </button>
              <button
                className={`${styles.iconButton} ${styles.danger}`}
                aria-label={`Delete ${target.name}`}
                onClick={() => setDeleteTarget(target)}
              >
                <Trash2 size={15} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {isCreating && (
        <NotificationTargetModal onSaved={handleSaved} onClose={() => setIsCreating(false)} />
      )}

      {editTarget && (
        <NotificationTargetModal
          target={editTarget}
          onSaved={handleSaved}
          onClose={() => setEditTarget(null)}
        />
      )}

      {deleteTarget && (
        <ConfirmModal
          title="Delete notification target"
          message={`"${deleteTarget.name}" will stop receiving messages. Its URL is not recoverable afterwards.`}
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
