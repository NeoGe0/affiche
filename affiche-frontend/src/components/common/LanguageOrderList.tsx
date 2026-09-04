import { useEffect, useRef, useState } from 'react';
import { ChevronUp, ChevronDown, Plus, X } from 'lucide-react';

import { ORDERABLE_LANGUAGES, languageLabel } from '../../constants/languages';
import { ReorderableList } from './ReorderableList';
import { moveItem } from './reorder';
import rowStyles from './ReorderableList.module.css';
import styles from './LanguageOrderList.module.css';

interface LanguageOrderListProps {

  languages: string[];
  onChange: (order: string[]) => void;
  disabled?: boolean;
}

export function LanguageOrderList({ languages, onChange, disabled = false }: LanguageOrderListProps) {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const addRef = useRef<HTMLDivElement>(null);

  const available = ORDERABLE_LANGUAGES.filter((lang) => !languages.includes(lang.value));

  useEffect(() => {
    if (!isAddOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (addRef.current && !addRef.current.contains(e.target as Node)) setIsAddOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [isAddOpen]);

  const add = (value: string) => {
    setIsAddOpen(false);
    onChange([...languages, value]);
  };

  const remove = (index: number) => {
    if (languages.length <= 1) return;
    onChange(languages.filter((_, i) => i !== index));
  };

  return (
    <div className={styles.wrapper}>
      <ReorderableList
        order={languages}
        onChange={onChange}
        disabled={disabled}
        label={languageLabel}
        renderActions={(language, index) => (
          <>
            <button
              type="button"
              className={rowStyles.rowButton}
              onClick={() => onChange(moveItem(languages, index, index - 1))}
              disabled={index === 0 || disabled}
              title="Move up"
              aria-label={`Move ${languageLabel(language)} up`}
            >
              <ChevronUp size={18} />
            </button>
            <button
              type="button"
              className={rowStyles.rowButton}
              onClick={() => onChange(moveItem(languages, index, index + 1))}
              disabled={index === languages.length - 1 || disabled}
              title="Move down"
              aria-label={`Move ${languageLabel(language)} down`}
            >
              <ChevronDown size={18} />
            </button>
            <button
              type="button"
              className={rowStyles.rowButton}
              onClick={() => remove(index)}
              disabled={languages.length <= 1 || disabled}
              title={languages.length <= 1 ? 'At least one language is required' : 'Remove'}
              aria-label={`Remove ${languageLabel(language)}`}
            >
              <X size={16} />
            </button>
          </>
        )}
      />

      <div className={styles.add} ref={addRef}>
        <button
          type="button"
          className={styles.addButton}
          onClick={() => setIsAddOpen((open) => !open)}
          disabled={disabled || available.length === 0}
          title={available.length === 0 ? 'Every language is already in the list' : 'Add a language'}
          aria-haspopup="menu"
          aria-expanded={isAddOpen}
        >
          <Plus size={16} />
          Add language
        </button>

        {isAddOpen && available.length > 0 && (
          <div className={styles.addDropdown} role="menu">
            {available.map((lang) => (
              <button
                key={lang.value || 'textless'}
                type="button"
                role="menuitem"
                className={styles.addItem}
                onClick={() => add(lang.value)}
              >
                {lang.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
