import { libraryApi } from '../api';
import type { TaskKind } from '../types';
import type { Library, SyncTaskResponse } from '../types';

export type LibraryActionName = 'sync' | 'generate' | 'upload' | 'reset';

export interface LibraryActionScope {
  mediaServerId: number;

  library?: Library;

  includeUnprocessed: boolean;
}

export interface LibraryActionSpec {

  request: (scope: LibraryActionScope) => Promise<SyncTaskResponse>;

  taskKind?: TaskKind;
  errorTitle: string;

  errorFallback: string;
}

export const LIBRARY_ACTIONS: Record<LibraryActionName, LibraryActionSpec> = {
  sync: {
    request: ({ mediaServerId, library }) =>
      library
        ? libraryApi.syncLibrary(library.media_server_id, library.id)
        : libraryApi.syncAllLibraries(mediaServerId),
    taskKind: 'sync',
    errorTitle: 'Sync failed',
    errorFallback: 'Could not start the library sync.',
  },
  generate: {
    request: ({ mediaServerId, library }) =>
      library
        ? libraryApi.syncLibraryPosters(library.media_server_id, library.id)
        : libraryApi.syncAllPosters(mediaServerId),
    taskKind: 'generate',
    errorTitle: 'Generation failed',
    errorFallback: 'Could not start the poster generation.',
  },
  upload: {
    request: ({ mediaServerId, library }) =>
      library
        ? libraryApi.uploadLibraryPosters(library.media_server_id, library.id)
        : libraryApi.uploadAllPosters(mediaServerId),
    errorTitle: 'Upload failed',
    errorFallback: 'Could not start the poster upload.',
  },
  reset: {
    request: ({ mediaServerId, library, includeUnprocessed }) =>
      library
        ? libraryApi.resetLibraryPosters(library.media_server_id, library.id, includeUnprocessed)
        : libraryApi.resetAllPosters(mediaServerId, includeUnprocessed),
    taskKind: 'reset',
    errorTitle: 'Reset failed',
    errorFallback: 'Could not start the poster reset.',
  },
};
