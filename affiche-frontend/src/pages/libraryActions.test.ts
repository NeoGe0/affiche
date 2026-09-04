import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LIBRARY_ACTIONS } from './libraryActions';
import { libraryApi } from '../api';
import type { Library } from '../types';

vi.mock('../api', () => ({
  libraryApi: {
    syncLibrary: vi.fn(),
    syncAllLibraries: vi.fn(),
    syncLibraryPosters: vi.fn(),
    syncAllPosters: vi.fn(),
    uploadLibraryPosters: vi.fn(),
    uploadAllPosters: vi.fn(),
    resetLibraryPosters: vi.fn(),
    resetAllPosters: vi.fn(),
  },
}));

const LIBRARY: Library = { id: 7, media_server_id: 4, name: 'Movies', library_type: 'movie' };

const scope = (library?: Library) => ({ mediaServerId: 1, library, includeUnprocessed: false });

beforeEach(() => {
  vi.resetAllMocks();
});

describe('LIBRARY_ACTIONS scoped to one library', () => {
  it.each([
    ['sync', 'syncLibrary'],
    ['generate', 'syncLibraryPosters'],
    ['upload', 'uploadLibraryPosters'],
    ['reset', 'resetLibraryPosters'],
  ] as const)('%s calls %s with the library\'s own server', async (action, method) => {
    await LIBRARY_ACTIONS[action].request(scope(LIBRARY));

    expect(vi.mocked(libraryApi[method]).mock.calls[0].slice(0, 2)).toEqual([4, 7]);
  });
});

describe('LIBRARY_ACTIONS across all libraries', () => {
  it.each([
    ['sync', 'syncAllLibraries'],
    ['generate', 'syncAllPosters'],
    ['upload', 'uploadAllPosters'],
    ['reset', 'resetAllPosters'],
  ] as const)('%s calls %s with the page\'s media server', async (action, method) => {
    await LIBRARY_ACTIONS[action].request(scope());

    expect(vi.mocked(libraryApi[method]).mock.calls[0][0]).toBe(1);
  });
});

describe('LIBRARY_ACTIONS reset opt-in', () => {
  it('forwards the "also reset unprocessed" flag to the scoped endpoint', async () => {
    await LIBRARY_ACTIONS.reset.request({ ...scope(LIBRARY), includeUnprocessed: true });

    expect(libraryApi.resetLibraryPosters).toHaveBeenCalledWith(4, 7, true);
  });

  it('forwards it to the all-libraries endpoint too', async () => {
    await LIBRARY_ACTIONS.reset.request({ ...scope(), includeUnprocessed: true });

    expect(libraryApi.resetAllPosters).toHaveBeenCalledWith(1, true);
  });

  it('is the only action that reads the flag', async () => {
    await LIBRARY_ACTIONS.sync.request({ ...scope(LIBRARY), includeUnprocessed: true });

    expect(libraryApi.syncLibrary).toHaveBeenCalledWith(4, 7);
  });
});

describe('LIBRARY_ACTIONS metadata', () => {
  it('drives the header progress bar for the long per-item tasks', () => {
    expect(LIBRARY_ACTIONS.sync.taskKind).toBe('sync');
    expect(LIBRARY_ACTIONS.generate.taskKind).toBe('generate');
    expect(LIBRARY_ACTIONS.reset.taskKind).toBe('reset');

    expect(LIBRARY_ACTIONS.upload.taskKind).toBeUndefined();
  });

  it('gives every action a toast title and a fallback sentence', () => {
    for (const spec of Object.values(LIBRARY_ACTIONS)) {
      expect(spec.errorTitle).toBeTruthy();
      expect(spec.errorFallback).toMatch(/\.$/);
    }
  });
});
