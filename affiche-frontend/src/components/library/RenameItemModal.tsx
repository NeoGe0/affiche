import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { errorMessage, libraryApi } from '../../api';
import { useToast } from '../../context/ToastContext';
import { Modal } from '../common';
import {
  noSuggestionMessage, preselectedOption, renameOptions, type RenameOption,
} from './renameOptions';
import styles from './RenameItemModal.module.css';

interface RenameItemModalProps {
  mediaServerId: number;
  libraryId: number;
  itemId: number;

  currentTitle: string;

  mediaServerName?: string;

  isBusy?: boolean;

  onConfirm: (title: string, regenerate: boolean) => void;
  onClose: () => void;
}

export function RenameItemModal({
  mediaServerId,
  libraryId,
  itemId,
  currentTitle,
  mediaServerName,
  isBusy = false,
  onConfirm,
  onClose,
}: RenameItemModalProps) {
  const toast = useToast();
  const [title, setTitle] = useState(currentTitle);
  const [regenerate, setRegenerate] = useState(true);
  const [options, setOptions] = useState<RenameOption[] | null>(null);

  const [emptyMessage, setEmptyMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const suggestions = await libraryApi.suggestItemTitles(mediaServerId, libraryId, itemId);
        if (cancelled) return;
        const loaded = renameOptions(suggestions);
        setOptions(loaded);
        setEmptyMessage(noSuggestionMessage(suggestions));

        const preselected = preselectedOption(loaded);
        if (preselected) setTitle((typed) => (typed === currentTitle ? preselected.title : typed));
      } catch (error) {
        if (cancelled) return;

        setOptions([]);
        setEmptyMessage('Could not reach the catalogue just now. Type the title you want below.');
        toast.error(errorMessage(error, 'Could not look up this title.'), { title: 'Rename' });
      }
    };
    load();
    return () => { cancelled = true; };
  }, [mediaServerId, libraryId, itemId, currentTitle, toast]);

  const trimmed = title.trim();
  const canRename = !!trimmed && trimmed !== currentTitle && !isBusy;
  const serverName = mediaServerName || 'your media server';

  return (
    <Modal
      size="large"
      label="Rename this item"
      title="Rename this item"
      description={
        <>
          Affiche writes the new title to <strong>{serverName}</strong> and locks the field, so a
          metadata refresh will not undo it. Files on disk are not touched.
        </>
      }
      isBusy={isBusy}
      onClose={onClose}
      footer={
        <>
          <button className={styles.secondary} onClick={onClose} disabled={isBusy}>Cancel</button>
          <button
            className={styles.primary}
            onClick={() => onConfirm(trimmed, regenerate)}
            disabled={!canRename}
          >
            {isBusy ? <Loader2 size={16} className="spin" /> : null}
            Rename
          </button>
        </>
      }
    >
      <div className={styles.content}>
        <section className={styles.section}>
          <h3 className={styles.sectionHeading}>Now</h3>
          <p className={styles.current}>{currentTitle}</p>
        </section>

        <section className={styles.section}>
          <h3 className={styles.sectionHeading}>
            Suggestion
            {options === null && (
              <span className={styles.searching}>
                <Loader2 size={13} className="spin" aria-hidden="true" />
                checking…
              </span>
            )}
          </h3>
          {options !== null && options.length === 0 ? (
            <p className={styles.empty}>{emptyMessage}</p>
          ) : (
            <div className={styles.list} role="radiogroup" aria-label="Suggested title">
              {(options ?? []).map((option) => (
                <label key={option.title} className={styles.row}>
                  <input
                    type="radio"
                    name="suggested-title"
                    checked={trimmed === option.title}
                    onChange={() => setTitle(option.title)}
                    disabled={isBusy}
                  />
                  <span className={styles.rowTitle}>{option.title}</span>
                  <span className={`${styles.rowNote} ${styles.certain}`}>{option.source}</span>
                </label>
              ))}
            </div>
          )}
        </section>

        <section className={styles.section}>
          <label className={styles.fieldLabel} htmlFor="rename-title">Title</label>
          <input
            id="rename-title"
            className={styles.field}
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && canRename) onConfirm(trimmed, regenerate); }}
            disabled={isBusy}
            autoFocus
          />
        </section>

        <label className={styles.checkbox}>
          <input
            type="checkbox"
            checked={regenerate}
            onChange={(e) => setRegenerate(e.target.checked)}
            disabled={isBusy}
          />
          <span>
            Regenerate the poster afterwards
            <span className={styles.checkboxNote}>
              The poster carries the old title until it is made again.
            </span>
          </span>
        </label>
      </div>
    </Modal>
  );
}
