import { useSyncExternalStore } from 'react';

import { fontsApi } from '../api';
import { API_BASE } from '../api/client';

import { fontBaseName } from '../components/image/fontName';

interface FontsState {

  fonts: string[] | null;
  isLoading: boolean;
}

const EMPTY: FontsState = { fonts: null, isLoading: true };

const NONE: string[] = [];

let state: FontsState = EMPTY;
let inFlight: Promise<void> | null = null;

let generation = 0;
const listeners = new Set<() => void>();

const injected = new Set<string>();

function publish(next: FontsState) {
  state = next;
  listeners.forEach((notify) => notify());
}

function injectFontFaces(fonts: string[]) {
  const missing = fonts.filter((f) => !injected.has(f));
  if (missing.length === 0) return;

  const style = document.createElement('style');
  style.dataset.afficheFonts = 'true';
  style.textContent = missing
    .map((file) => {
      const family = fontBaseName(file);
      const url = `${API_BASE}/service/fonts/${encodeURIComponent(file)}`;
      return `@font-face { font-family: "${family}"; src: url("${url}") format("truetype"); font-display: swap; }`;
    })
    .join('\n');
  document.head.appendChild(style);
  missing.forEach((f) => injected.add(f));
}

function startFetch(): Promise<void> {
  const requested = generation;
  const isCurrent = () => requested === generation;

  inFlight = fontsApi
    .getFonts()
    .then((fonts) => {
      if (!isCurrent()) return;
      injectFontFaces(fonts);
      publish({ fonts, isLoading: false });
    })
    .catch(() => {

      if (isCurrent()) publish({ fonts: null, isLoading: false });
    })
    .finally(() => {
      if (isCurrent()) inFlight = null;
    });

  return inFlight;
}

function ensureLoaded() {
  if (state.fonts || inFlight) return;
  void startFetch();
}

export async function reloadFonts(): Promise<string[]> {
  generation += 1;
  inFlight = null;
  const fonts = await fontsApi.getFonts();
  injectFontFaces(fonts);
  publish({ fonts, isLoading: false });
  return fonts;
}

export function resetFontsStore() {
  generation += 1;
  inFlight = null;
  state = EMPTY;
  listeners.clear();
  injected.clear();
  document.head
    .querySelectorAll('style[data-affiche-fonts]')
    .forEach((element) => element.remove());
}

function subscribe(listener: () => void) {
  listeners.add(listener);

  ensureLoaded();
  return () => {
    listeners.delete(listener);
  };
}

const getSnapshot = () => state;

export function useFonts() {
  const { fonts, isLoading } = useSyncExternalStore(subscribe, getSnapshot);
  return { fonts: fonts ?? NONE, isLoading, reload: reloadFonts };
}
