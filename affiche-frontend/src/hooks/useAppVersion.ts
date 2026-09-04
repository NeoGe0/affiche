import { useSyncExternalStore } from 'react';

import { settingsApi } from '../api';

let version: string | null = null;

let attempted = false;
const listeners = new Set<() => void>();

function ensureLoaded() {
  if (attempted) return;
  attempted = true;

  void settingsApi
    .getSettingsInfo()
    .then((info) => {
      version = info.version ?? null;
      listeners.forEach((notify) => notify());
    })

    .catch(() => {});
}

export function resetAppVersionStore() {
  version = null;
  attempted = false;
  listeners.clear();
}

function subscribe(listener: () => void) {
  listeners.add(listener);

  ensureLoaded();
  return () => {
    listeners.delete(listener);
  };
}

const getSnapshot = () => version;

export function useAppVersion() {
  const current = useSyncExternalStore(subscribe, getSnapshot);
  return { version: current, isPrerelease: current !== null && current.includes('-') };
}
