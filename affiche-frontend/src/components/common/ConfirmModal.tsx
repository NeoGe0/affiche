import { AlertTriangle } from 'lucide-react';
import { Modal } from './Modal';
import styles from './ConfirmModal.module.css';

interface ConfirmModalProps {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'default' | 'danger';

  checkboxLabel?: string;
  checkboxChecked?: boolean;
  onCheckboxChange?: (checked: boolean) => void;

  isBusy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  checkboxLabel,
  checkboxChecked = false,
  onCheckboxChange,
  isBusy = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  return (
    <Modal

      label={title}
      isBusy={isBusy}
      onClose={onCancel}
      footer={
        <>
          <button
            className={`${styles.button} ${styles.cancel}`}
            onClick={onCancel}
            disabled={isBusy}
          >
            {cancelLabel}
          </button>
          <button
            className={`${styles.button} ${variant === 'danger' ? styles.danger : styles.confirm}`}
            onClick={onConfirm}
            disabled={isBusy}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <div className={styles.content}>
        <div className={`${styles.icon} ${variant === 'danger' ? styles.danger : ''}`}>
          <AlertTriangle size={24} />
        </div>
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.message}>{message}</p>
        {checkboxLabel && (
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={checkboxChecked}
              onChange={(e) => onCheckboxChange?.(e.target.checked)}
            />
            <span>{checkboxLabel}</span>
          </label>
        )}
      </div>
    </Modal>
  );
}
