import { CheckSquare, Image, Lock, RotateCcw, Unlock, Upload, X } from 'lucide-react';

import styles from './SelectionBar.module.css';

interface SelectionBarProps {
  count: number;

  allSelected: boolean;
  isBusy?: boolean;
  onToggleAll: () => void;
  onClear: () => void;
  onGenerate: () => void;
  onUpload: () => void;
  onLock: () => void;
  onUnlock: () => void;
  onReset: () => void;
}

export function SelectionBar({
  count,
  allSelected,
  isBusy = false,
  onToggleAll,
  onClear,
  onGenerate,
  onUpload,
  onLock,
  onUnlock,
  onReset,
}: SelectionBarProps) {
  return (
    <div className={styles.bar} role="region" aria-label="Selection actions">
      {
}
      <button className={styles.selectAll} onClick={onToggleAll} disabled={isBusy}>
        <CheckSquare size={15} />
        {allSelected ? 'Clear all' : 'Select all'}
      </button>

      <span className={styles.count}>
        {count} selected
      </span>

      <div className={styles.actions}>
        <button className={styles.action} onClick={onGenerate} disabled={isBusy || count === 0}>
          <Image size={15} />
          Generate
        </button>
        <button className={styles.action} onClick={onUpload} disabled={isBusy || count === 0}>
          <Upload size={15} />
          Upload
        </button>
        <button className={styles.action} onClick={onLock} disabled={isBusy || count === 0}>
          <Lock size={15} />
          Lock
        </button>
        <button className={styles.action} onClick={onUnlock} disabled={isBusy || count === 0}>
          <Unlock size={15} />
          Unlock
        </button>
        <button className={`${styles.action} ${styles.danger}`} onClick={onReset} disabled={isBusy || count === 0}>
          <RotateCcw size={15} />
          Reset
        </button>
      </div>

      <button className={styles.close} onClick={onClear} disabled={isBusy} aria-label="Leave select mode">
        <X size={16} />
      </button>
    </div>
  );
}
