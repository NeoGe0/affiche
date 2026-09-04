import { useState } from 'react';
import { ProviderOrderList } from '../common';
import styles from './ProviderOrderForm.module.css';

interface ProviderOrderFormProps {
  title: string;
  description: string;
  providers: string[];
  onSave: (order: string[]) => Promise<void>;
  isSaving: boolean;
}

export function ProviderOrderForm({
  title,
  description,
  providers,
  onSave,
  isSaving,
}: ProviderOrderFormProps) {
  const [order, setOrder] = useState<string[]>(providers);
  const [hasChanges, setHasChanges] = useState(false);

  const handleChange = (next: string[]) => {
    setOrder(next);
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      await onSave(order);
      setHasChanges(false);
    } catch {}
  };

  const handleReset = () => {
    setOrder(providers);
    setHasChanges(false);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        <p className={styles.description}>{description}</p>
      </div>

      <ProviderOrderList providers={order} onChange={handleChange} disabled={isSaving} />

      {hasChanges && (
        <div className={styles.footer}>
          <button
            className={styles.resetButton}
            onClick={handleReset}
            disabled={isSaving}
          >
            Reset
          </button>
          <button
            className={styles.saveButton}
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? 'Saving...' : 'Save Order'}
          </button>
        </div>
      )}
    </div>
  );
}
