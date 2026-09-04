import { useState } from 'react';

import { Modal } from '../common';
import styles from './ItemPickerModal.module.css';

interface TitlePromptModalProps {
  heading: string;
  confirmLabel: string;
  initialTitle?: string;
  isBusy?: boolean;
  onConfirm: (title: string) => void;
  onClose: () => void;
}

export function TitlePromptModal({
  heading,
  confirmLabel,
  initialTitle = '',
  isBusy = false,
  onConfirm,
  onClose,
}: TitlePromptModalProps) {
  const [title, setTitle] = useState(initialTitle);
  const trimmed = title.trim();

  const submit = () => {
    if (trimmed) onConfirm(trimmed);
  };

  return (
    <Modal
      label={heading}
      isBusy={isBusy}
      onClose={onClose}
      footer={
        <>
          <button className={styles.secondary} onClick={onClose} disabled={isBusy}>Cancel</button>
          <button className={styles.primary} onClick={submit} disabled={isBusy || !trimmed}>
            {confirmLabel}
          </button>
        </>
      }
    >
      <div className={styles.content}>
        <h2 className={styles.heading}>{heading}</h2>
        <div className={styles.searchBox}>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder="Collection name"
            autoFocus
          />
        </div>
      </div>
    </Modal>
  );
}
