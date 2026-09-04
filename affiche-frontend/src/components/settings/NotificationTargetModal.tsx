import { useId, useState } from 'react';
import { CheckCircle, Loader, Send, XCircle } from 'lucide-react';

import { errorMessage, notificationsApi } from '../../api';
import { Modal } from '../common';
import { useToast } from '../../context/ToastContext';
import type { NotificationTarget, NotificationType } from '../../types';
import { canSubmit, NOTIFICATION_TYPES } from './notificationTarget';
import sectionStyles from './SettingsSection.module.css';
import styles from './NotificationTargetModal.module.css';

interface NotificationTargetModalProps {

  target?: NotificationTarget;
  onSaved: (target: NotificationTarget) => void;
  onClose: () => void;
}

export function NotificationTargetModal({
  target,
  onSaved,
  onClose,
}: NotificationTargetModalProps) {
  const toast = useToast();
  const uid = useId();
  const isEdit = target !== undefined;

  const [name, setName] = useState(target?.name ?? '');
  const [type, setType] = useState<NotificationType>(target?.type ?? 'discord');
  const [url, setUrl] = useState('');
  const [onTaskCompleted, setOnTaskCompleted] = useState(target?.on_task_completed ?? true);
  const [onTaskFailed, setOnTaskFailed] = useState(target?.on_task_failed ?? true);
  const [onItemsErrored, setOnItemsErrored] = useState(target?.on_items_errored ?? true);
  const [isSaving, setIsSaving] = useState(false);
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'delivered' | 'failed'>('idle');

  const typeHint = NOTIFICATION_TYPES.find((t) => t.value === type)?.hint ?? '';

  const canTest = Boolean(url.trim() || isEdit);

  const handleTest = async () => {
    if (!canTest) return;
    setTestStatus('testing');
    try {

      const typed = url.trim();
      const { delivered } = typed || !target
        ? await notificationsApi.testUrl({ type, url: typed, name: name.trim() || 'This target' })
        : await notificationsApi.testTarget(target.id);
      setTestStatus(delivered ? 'delivered' : 'failed');
    } catch (err) {
      setTestStatus('failed');
      toast.error(errorMessage(err, 'Could not send the test.'), { title: 'Notifications' });
    }
  };

  const handleSave = async () => {
    if (!canSubmit(name, url, isEdit)) return;
    setIsSaving(true);
    try {

      const payload = {
        name: name.trim(),
        type,
        on_task_completed: onTaskCompleted,
        on_task_failed: onTaskFailed,
        on_items_errored: onItemsErrored,
        ...(url.trim() ? { url: url.trim() } : {}),
      };
      const saved = target
        ? await notificationsApi.updateTarget(target.id, payload)
        : await notificationsApi.createTarget({ ...payload, url: url.trim() });
      onSaved(saved);
      onClose();
    } catch (err) {
      toast.error(errorMessage(err, `Could not ${isEdit ? 'save' : 'create'} the target.`), {
        title: 'Notifications',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const heading = isEdit ? `Edit ${target.name}` : 'New notification target';

  const footer = (
    <>
      <button className={sectionStyles.outlineButton} onClick={onClose} disabled={isSaving}>
        Cancel
      </button>
      <button
        className={sectionStyles.saveButton}
        onClick={handleSave}
        disabled={isSaving || !canSubmit(name, url, isEdit)}
      >
        {isSaving ? (isEdit ? 'Saving…' : 'Creating…') : isEdit ? 'Save target' : 'Create target'}
      </button>
    </>
  );

  return (
    <Modal
      size="drawer"
      label={heading}
      title={heading}
      description="Where to send a message when a background run ends."
      isBusy={isSaving}
      onClose={onClose}
      footer={footer}
    >
      <div className={styles.body}>
        <label className={styles.field} htmlFor={`${uid}-name`}>
          <span className={styles.label}>Name</span>
          <input
            id={`${uid}-name`}
            type="text"
            className={styles.input}
            placeholder="e.g. Home Discord"
            value={name}
            onChange={(e) => { setName(e.target.value); setTestStatus('idle'); }}
          />
        </label>

        <label className={styles.field} htmlFor={`${uid}-type`}>
          <span className={styles.label}>Service</span>
          <select
            id={`${uid}-type`}
            className={styles.input}
            value={type}
            onChange={(e) => { setType(e.target.value as NotificationType); setTestStatus('idle'); }}
          >
            {NOTIFICATION_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        {
}
        <div className={styles.field}>
          <label className={styles.label} htmlFor={`${uid}-url`}>
            URL
          </label>
          <input
            id={`${uid}-url`}
            type="text"
            className={styles.input}
            aria-describedby={`${uid}-url-hint`}
            placeholder={isEdit ? `Stored (${target.url_hint}) — leave blank to keep` : typeHint}
            value={url}
            onChange={(e) => { setUrl(e.target.value); setTestStatus('idle'); }}
          />
          <span id={`${uid}-url-hint`} className={sectionStyles.settingDescription}>
            {isEdit
              ? 'Only fill this in to replace the stored URL. It is never shown again once saved.'
              : typeHint}
          </span>

          {
}
          <div className={styles.testRow}>
            <button
              type="button"
              className={`${sectionStyles.validateButton} ${testStatus === 'delivered' ? sectionStyles.validated : ''} ${testStatus === 'failed' ? sectionStyles.failed : ''}`}
              onClick={handleTest}
              disabled={!canTest || testStatus === 'testing' || isSaving}
            >
              {testStatus === 'testing' && <Loader size={16} className={styles.spinning} />}
              {testStatus === 'delivered' && <CheckCircle size={16} />}
              {testStatus === 'failed' && <XCircle size={16} />}
              {testStatus === 'idle' && <Send size={16} />}
              {testStatus === 'testing' ? 'Sending…'
                : testStatus === 'delivered' ? 'Delivered'
                : testStatus === 'failed' ? 'Not delivered' : 'Send a test'}
            </button>
            {testStatus === 'failed' && (
              <span className={sectionStyles.settingDescription}>
                Nothing arrived. You can still save it — the URL is stored either way.
              </span>
            )}
          </div>
        </div>

        <fieldset className={styles.events}>
          <legend className={styles.label}>Notify me when</legend>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={onTaskCompleted}
              onChange={(e) => setOnTaskCompleted(e.target.checked)}
            />
            <span>A run finishes cleanly</span>
          </label>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={onTaskFailed}
              onChange={(e) => setOnTaskFailed(e.target.checked)}
            />
            <span>A run fails</span>
          </label>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={onItemsErrored}
              onChange={(e) => setOnItemsErrored(e.target.checked)}
            />
            <span>A run finishes but items are in an error state</span>
          </label>
        </fieldset>
      </div>
    </Modal>
  );
}
