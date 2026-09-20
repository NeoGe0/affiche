import { CheckSquare, Image, Lock, RotateCcw, Unlock, Upload, X } from 'lucide-react';

import { OverflowMenu } from '../common';
import styles from './SelectionBar.module.css';

interface SelectionBarProps {
  count: number;

  allSelected: boolean;

  matchingTotal?: number;

  isAllMatching?: boolean;
  onSelectAllMatching?: () => void;
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
  matchingTotal,
  isAllMatching = false,
  onSelectAllMatching,
  isBusy = false,
  onToggleAll,
  onClear,
  onGenerate,
  onUpload,
  onLock,
  onUnlock,
  onReset,
}: SelectionBarProps) {
  const canSelectAllMatching = !isAllMatching && !!onSelectAllMatching
    && matchingTotal !== undefined && matchingTotal > count;

  return (
    <div className={styles.bar} role="region" aria-label="Selection actions">
      {
}
      <button className={styles.selectAll} onClick={onToggleAll} disabled={isBusy}>
        <CheckSquare size={15} />
        {allSelected ? 'Clear all' : 'Select all'}
      </button>

      <span className={styles.count} aria-live="polite">
        {isAllMatching ? `All ${count.toLocaleString()} matching selected` : `${count.toLocaleString()} selected`}
      </span>

      {canSelectAllMatching && (
        <button className={styles.matching} onClick={onSelectAllMatching} disabled={isBusy}>
          Select all {matchingTotal.toLocaleString()} matching
        </button>
      )}

      <div className={styles.actions}>
        <button className={styles.action} onClick={onGenerate} disabled={isBusy || count === 0}>
          <Image size={15} />
          Generate
        </button>
        <button className={styles.action} onClick={onUpload} disabled={isBusy || count === 0}>
          <Upload size={15} />
          Upload
        </button>
        <OverflowMenu
          title="More selection actions"
          triggerClassName={styles.action}
          items={[
            { icon: <Lock size={16} />, label: 'Lock', onClick: onLock, disabled: isBusy || count === 0 },
            { icon: <Unlock size={16} />, label: 'Unlock', onClick: onUnlock, disabled: isBusy || count === 0 },
            { icon: <RotateCcw size={16} />, label: 'Reset', onClick: onReset, disabled: isBusy || count === 0, danger: true },
          ]}
        />
      </div>

      <button className={styles.close} onClick={onClear} disabled={isBusy} aria-label="Leave select mode">
        <X size={16} />
      </button>
    </div>
  );
}
