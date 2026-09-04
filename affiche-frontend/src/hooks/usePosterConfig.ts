import { useSyncExternalStore } from 'react';

import { settingsApi } from '../api';
import type { PosterConfig } from '../types';

interface PosterConfigState {
  config: PosterConfig | null;
  isLoading: boolean;
  error: Error | null;
}

const EMPTY: PosterConfigState = { config: null, isLoading: true, error: null };

let state: PosterConfigState = EMPTY;
let inFlight: Promise<void> | null = null;

let generation = 0;
const listeners = new Set<() => void>();

function publish(next: PosterConfigState) {
  state = next;
  listeners.forEach((notify) => notify());
}

function ensureLoaded() {
  if (state.config || inFlight) return;

  const requested = generation;
  const isCurrent = () => requested === generation;

  inFlight = settingsApi
    .getPosterConfig()
    .then((config) => {
      if (isCurrent()) publish({ config, isLoading: false, error: null });
    })
    .catch((err) => {
      if (isCurrent()) {
        publish({
          config: null,
          isLoading: false,
          error: err instanceof Error ? err : new Error('Failed to fetch poster config'),
        });
      }
    })
    .finally(() => {

      if (isCurrent()) inFlight = null;
    });
}

export function invalidatePosterConfig() {
  generation += 1;
  inFlight = null;
  publish(EMPTY);
  if (listeners.size > 0) ensureLoaded();
}

export function resetPosterConfigStore() {
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

export function usePosterConfig(): PosterConfigState {
  return useSyncExternalStore(subscribe, getSnapshot);
}
