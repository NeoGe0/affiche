import { providerLabel } from '../../constants/providers';
import { NO_PROVIDER } from '../../types';

export interface ProviderFilterOption {
  value: string;
  label: string;

  count?: number;
}

export function providerOptionLabel(provider: string): string {
  if (provider === NO_PROVIDER) return 'No source recorded';
  if (provider === 'server') return 'Media server artwork';
  if (provider === 'manual') return 'Chosen manually';
  return providerLabel(provider);
}

export function providerFilterOptions(
  providers: Record<string, number> | undefined,
  selected?: string
): ProviderFilterOption[] {
  const counted = Object.entries(providers ?? {});
  const named = counted
    .filter(([provider]) => provider !== NO_PROVIDER)
    .sort(([aName, aCount], [bName, bCount]) => bCount - aCount || aName.localeCompare(bName));

  const unrecorded = counted.filter(([provider]) => provider === NO_PROVIDER);

  const options: ProviderFilterOption[] = [
    { value: '', label: 'Any source', count: providers && counted.reduce((n, [, c]) => n + c, 0) },
    ...[...named, ...unrecorded].map(([provider, count]) => ({
      value: provider,
      label: providerOptionLabel(provider),
      count,
    })),
  ];

  return options.some((option) => option.value === (selected ?? ''))
    ? options
    : [...options, { value: selected!, label: providerOptionLabel(selected!) }];
}
