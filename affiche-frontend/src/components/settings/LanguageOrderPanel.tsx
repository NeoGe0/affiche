import { Languages } from 'lucide-react';

import { LanguageOrderList } from '../common';
import sectionStyles from './SettingsSection.module.css';
import styles from './LanguageOrderPanel.module.css';

interface LanguageOrderPanelProps {

  languageOrder: string[];
  isSaving: boolean;
  onChange: (order: string[]) => void;
}

export function LanguageOrderPanel({ languageOrder, isSaving, onChange }: LanguageOrderPanelProps) {
  return (
    <div className={sectionStyles.divider}>
      <div className={styles.header}>
        <Languages size={16} className={styles.icon} />
        <span className={styles.title}>Artwork languages</span>
      </div>
      <p className={styles.description}>
        Poster generation tries these in order and keeps the first match — every provider is
        searched for a language before moving on to the next one. Textless posters carry no title
        of their own, which is usually what you want under a generated title.
      </p>
      <LanguageOrderList languages={languageOrder} onChange={onChange} disabled={isSaving} />
    </div>
  );
}
