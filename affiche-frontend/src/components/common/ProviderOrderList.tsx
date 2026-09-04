import { ChevronUp, ChevronDown } from 'lucide-react';

import { providerLabel } from '../../constants/providers';
import { ReorderableList } from './ReorderableList';
import { moveItem } from './reorder';
import styles from './ReorderableList.module.css';

interface ProviderOrderListProps {

  providers: string[];
  onChange: (order: string[]) => void;
  disabled?: boolean;
}

export function ProviderOrderList({ providers, onChange, disabled = false }: ProviderOrderListProps) {
  return (
    <ReorderableList
      order={providers}
      onChange={onChange}
      disabled={disabled}
      label={providerLabel}
      renderActions={(provider, index) => (
        <>
          {
}
          <button
            type="button"
            className={styles.rowButton}
            onClick={() => onChange(moveItem(providers, index, index - 1))}
            disabled={index === 0 || disabled}
            title="Move up"
            aria-label={`Move ${providerLabel(provider)} up`}
          >
            <ChevronUp size={18} />
          </button>
          <button
            type="button"
            className={styles.rowButton}
            onClick={() => onChange(moveItem(providers, index, index + 1))}
            disabled={index === providers.length - 1 || disabled}
            title="Move down"
            aria-label={`Move ${providerLabel(provider)} down`}
          >
            <ChevronDown size={18} />
          </button>
        </>
      )}
    />
  );
}
