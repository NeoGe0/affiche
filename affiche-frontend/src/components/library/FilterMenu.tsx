import { useId, useState } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';

import { usePopoverDismiss } from '../../hooks/usePopoverDismiss';
import type { ItemFilter, LibraryItemCounts } from '../../types';
import {
  activeFilterChips, formatFilterCount, STATUS_FILTER_OPTIONS,
} from './listingFilters';
import { providerFilterOptions } from './providerFilter';

import styles from './FilterMenu.module.css';

interface FilterMenuProps {
  filter: ItemFilter;
  onFilterChange: (filter: ItemFilter) => void;

  provider?: string;
  onProviderChange: (provider: string | undefined) => void;

  counts?: LibraryItemCounts;
}

export function FilterMenu({
  filter, onFilterChange, provider, onProviderChange, counts,
}: FilterMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = usePopoverDismiss<HTMLDivElement>(isOpen, () => setIsOpen(false));

  const groupId = useId();
  const statusName = `${groupId}-status`;
  const sourceName = `${groupId}-source`;

  const chips = activeFilterChips(filter, provider);
  const sourceOptions = providerFilterOptions(counts?.providers, provider);

  const clearChip = (facet: 'status' | 'source') => {
    if (facet === 'status') onFilterChange('all');
    else onProviderChange(undefined);
  };

  return (
    <div className={styles.filters}>
      <div className={styles.menu} ref={menuRef}>
        <button
          type="button"
          className={`${styles.trigger} ${isOpen ? styles.triggerOpen : ''}`}
          onClick={() => setIsOpen((open) => !open)}
          aria-haspopup="dialog"
          aria-expanded={isOpen}
        >
          <SlidersHorizontal size={16} />
          <span className={styles.triggerLabel}>Filters</span>
          {chips.length > 0 && <span className={styles.badge}>{chips.length}</span>}
        </button>

        {isOpen && (
          <div className={styles.panel} role="dialog" aria-label="Filter items">
            <fieldset className={styles.section}>
              <legend className={styles.sectionTitle}>Status</legend>
              {STATUS_FILTER_OPTIONS.map((option) => (
                <label key={option.value} className={styles.row}>
                  <input
                    type="radio"
                    className={styles.radio}
                    name={statusName}
                    checked={filter === option.value}
                    onChange={() => onFilterChange(option.value)}
                  />
                  <span className={styles.rowLabel}>{option.label}</span>
                  {
}
                  {' '}
                  <span className={styles.rowCount}>
                    {formatFilterCount(counts?.[option.count])}
                  </span>
                </label>
              ))}
            </fieldset>

            <fieldset className={styles.section}>
              <legend className={styles.sectionTitle}>Poster source</legend>
              {
}
              <div className={styles.sourceRows}>
                {sourceOptions.map((option) => (
                  <label key={option.value} className={styles.row}>
                    <input
                      type="radio"
                      className={styles.radio}
                      name={sourceName}
                      checked={(provider ?? '') === option.value}
                      onChange={() => onProviderChange(option.value || undefined)}
                    />
                    <span className={styles.rowLabel}>{option.label}</span>
                    {' '}
                    <span className={styles.rowCount}>{formatFilterCount(option.count)}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
        )}
      </div>

      {chips.map((chip) => (
        <button
          key={chip.facet}
          type="button"
          className={styles.chip}
          onClick={() => clearChip(chip.facet)}
          title={`Remove the ${chip.label} filter`}
        >
          <span className={styles.chipLabel}>{chip.label}</span>
          <X size={13} />
        </button>
      ))}
    </div>
  );
}
