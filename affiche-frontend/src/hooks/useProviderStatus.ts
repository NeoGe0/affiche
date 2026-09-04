import { useSyncExternalStore } from 'react';

import { configApi } from '../api';
import { POSTER_PROVIDERS, providerRequiresApiKey, providerUrlMode } from '../constants/providers';

interface ProviderStatusState {

  configured: string[] | null;

  added: string[] | null;
  isLoading: boolean;
}

const EMPTY: ProviderStatusState = { configured: null, added: null, isLoading: true };

const NONE: string[] = [];

let state: ProviderStatusState = EMPTY;
let inFlight: Promise<void> | null = null;

let generation = 0;
const listeners = new Set<() => void>();

function publish(next: ProviderStatusState) {
  state = next;
  listeners.forEach((notify) => notify());
}

async function fetchStatus(): Promise<{ configured: string[]; added: string[] }> {
  const rows = await configApi.findConfigs('PROVIDER');
  const byName = new Map(rows.map((row) => [row.name, row]));

  const added = POSTER_PROVIDERS.filter((provider) => byName.has(provider));
  const configured = added.filter((provider) => {
    const row = byName.get(provider)!;
    if (!row.enabled) return false;

    if (providerUrlMode(provider) !== 'none' && !row.url) return false;

    return row.configured || !providerRequiresApiKey(provider);
  });

  return { configured, added };
}

function startFetch(): Promise<void> {
  const requested = generation;
  const isCurrent = () => requested === generation;

  inFlight = fetchStatus()
    .then(({ configured, added }) => {
      if (isCurrent()) publish({ configured, added, isLoading: false });
    })
    .catch(() => {

      if (isCurrent()) publish({ configured: null, added: null, isLoading: false });
    })
    .finally(() => {

      if (isCurrent()) inFlight = null;
    });

  return inFlight;
}

function ensureLoaded() {
  if (state.configured || inFlight) return;
  void startFetch();
}

export function reloadProviderStatus(): Promise<void> {
  generation += 1;
  inFlight = null;
  publish({ ...state, isLoading: true });
  return startFetch();
}

export function resetProviderStatusStore() {
  generation += 1;
  inFlight = null;
  state = EMPTY;
  listeners.clear();
}

function subscribe(listener: () => void) {
  listeners.add(listener);

  ensureLoaded();
  return () => {
    listeners.delete(listener);
  };
}

const getSnapshot = () => state;

export function useProviderStatus() {
  const { configured, added, isLoading } = useSyncExternalStore(subscribe, getSnapshot);
  const configuredProviders = configured ?? NONE;

  return {
    isAnyProviderConfigured: configuredProviders.length > 0,
    configuredProviders,
    addedProviders: added ?? NONE,
    isLoading,
    reload: reloadProviderStatus,
  };
}
