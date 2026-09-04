import type { ItemFilter, ItemStatusCounts } from '../../types';
import { providerOptionLabel } from './providerFilter';

export const STATUS_FILTER_OPTIONS: {
  value: ItemFilter;
  label: string;
  count: keyof ItemStatusCounts;
}[] = [
  { value: 'all', label: 'All items', count: 'total' },
  { value: 'unprocessed', label: 'Unprocessed', count: 'unprocessed' },
  { value: 'errors', label: 'With errors', count: 'errors' },
  { value: 'locked', label: 'Locked', count: 'locked' },
];

export interface FilterChip {
  facet: 'status' | 'source';
  label: string;
}

export function activeFilterChips(filter: ItemFilter, provider?: string): FilterChip[] {
  const chips: FilterChip[] = [];
  if (filter !== 'all') {
    const status = STATUS_FILTER_OPTIONS.find((option) => option.value === filter);
    if (status) chips.push({ facet: 'status', label: status.label });
  }
  if (provider) chips.push({ facet: 'source', label: providerOptionLabel(provider) });
  return chips;
}

const NUMBER_FORMAT = new Intl.NumberFormat();

export function formatFilterCount(count: number | undefined): string {
  return count === undefined ? '' : NUMBER_FORMAT.format(count);
}
