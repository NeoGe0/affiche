import { useEffect, useEffectEvent, useState } from 'react';

import { errorMessage, libraryApi, mediaServerApi } from '../api';
import { useToast } from '../context/ToastContext';
import {
  defaultLibrarySettings,
  patchLibrarySettings,
  patchServer,
  replaceServer,
  toLibrarySettingsUpdate,
  withoutIds,
  type LibraryWithSettings,
  type ServerWithLibraries,
} from '../components/settings/mediaServerState';
import type {
  Library,
  LibrarySettings,
  MediaServerLibrary,
  MediaServerResponse,
  NewLibraryDefaults,
} from '../types';

async function loadLibrary(serverId: number, library: Library): Promise<LibraryWithSettings> {
  try {
    return { library, settings: await libraryApi.getLibrarySettings(serverId, library.id) };
  } catch {
    return { library, settings: defaultLibrarySettings(library.id) };
  }
}

async function loadServer(
  entry: ServerWithLibraries['server']
): Promise<ServerWithLibraries> {
  try {
    const libraries = await libraryApi.getLibraries(entry.id);
    return {
      server: entry,
      libraries: await Promise.all(libraries.map((lib) => loadLibrary(entry.id, lib))),
    };
  } catch {
    return { server: entry, libraries: [] };
  }
}

async function loadTree(): Promise<ServerWithLibraries[]> {
  const servers = await mediaServerApi.getAll();
  return Promise.all(servers.map(loadServer));
}

interface UseMediaServersOptions {

  onServersChanged?: () => void;
}

export function useMediaServers({ onServersChanged }: UseMediaServersOptions = {}) {
  const toast = useToast();

  const [servers, setServers] = useState<ServerWithLibraries[]>([]);
  const [dirtyLibraries, setDirtyLibraries] = useState<Set<number>>(new Set());

  const [dirtyServers, setDirtyServers] = useState<Set<number>>(new Set());
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [webhookBusy, setWebhookBusy] = useState<number | null>(null);

  const [tokenBusy, setTokenBusy] = useState<number | null>(null);

  const [availableLibraries, setAvailableLibraries] = useState<MediaServerLibrary[]>([]);
  const [isLoadingAvailable, setIsLoadingAvailable] = useState(false);
  const [isAddingLibraries, setIsAddingLibraries] = useState(false);

  const reportError = (error: unknown, title: string, fallback: string) => {
    toast.error(errorMessage(error, fallback), { title });
  };

  const reload = async () => {
    try {
      setServers(await loadTree());
    } catch (error) {
      reportError(error, 'Media servers', 'Failed to load media servers');
    }
  };

  const loadOnMount = useEffectEvent(() => {
    reload();
  });

  useEffect(() => {
    loadOnMount();
  }, []);

  const changeLibrarySettings = (
    serverId: number,
    libraryId: number,
    patch: Partial<LibrarySettings>
  ) => {
    setServers((prev) => patchLibrarySettings(prev, serverId, libraryId, patch));
    setDirtyLibraries((prev) => new Set(prev).add(libraryId));
  };

  const changeServerSettings = (serverId: number, patch: Partial<MediaServerResponse>) => {
    setServers((prev) => patchServer(prev, serverId, patch));
    setDirtyServers((prev) => new Set(prev).add(serverId));
  };

  const changeLanguageOrder = (serverId: number, languageOrder: string[]) =>
    changeServerSettings(serverId, { language_order: languageOrder });

  const changePosterFallback = (serverId: number, patch: Partial<MediaServerResponse>) =>
    changeServerSettings(serverId, patch);

  const saveServer = async (serverId: number) => {
    const entry = servers.find((s) => s.server.id === serverId);
    if (!entry) return;

    const dirty = entry.libraries.filter((l) => dirtyLibraries.has(l.library.id));
    const serverDirty = dirtyServers.has(serverId);
    if (dirty.length === 0 && !serverDirty) return;

    const saveServerSettings = async () => {
      if (!serverDirty) return null;
      await mediaServerApi.setLanguageOrder(serverId, entry.server.language_order);
      return mediaServerApi.setPosterFallback(serverId, {
        fallback_to_server_poster: entry.server.fallback_to_server_poster,
        skip_style_when_not_textless: entry.server.skip_style_when_not_textless,
      });
    };

    setIsSaving(true);
    try {
      const [updatedServer] = await Promise.all([
        saveServerSettings(),
        Promise.all(
          dirty.map(({ library, settings }) =>
            libraryApi.updateLibrarySettings(serverId, library.id, toLibrarySettingsUpdate(settings))
          )
        ),
      ]);

      if (updatedServer) {
        setServers((prev) => replaceServer(prev, updatedServer));
        setDirtyServers((prev) => withoutIds(prev, [serverId]));
      }
      setDirtyLibraries((prev) => withoutIds(prev, dirty.map((l) => l.library.id)));
      toast.success('Server settings saved');
    } catch (error) {
      reportError(error, 'Server settings', 'Failed to save server settings');
    } finally {
      setIsSaving(false);
    }
  };

  const updateToken = async (serverId: number, token: string) => {
    setTokenBusy(serverId);
    try {
      const updated = await mediaServerApi.updateToken(serverId, token);
      setServers((prev) => replaceServer(prev, updated));
      toast.success('Token updated');
      return true;
    } catch (error) {
      reportError(error, 'Update token', 'Failed to update the token');
      return false;
    } finally {
      setTokenBusy(null);
    }
  };

  const runWebhookAction = async (
    serverId: number,
    action: () => Promise<void>,
    title = 'Webhook'
  ) => {
    setWebhookBusy(serverId);
    try {
      await action();
    } catch (error) {
      reportError(error, title, 'Webhook request failed');
    } finally {
      setWebhookBusy(null);
    }
  };

  const toggleWebhook = (serverId: number, enabled: boolean) =>
    runWebhookAction(serverId, async () => {
      const updated = await mediaServerApi.setWebhook(serverId, enabled);
      setServers((prev) => replaceServer(prev, updated));
    });

  const regenerateWebhook = (serverId: number) =>
    runWebhookAction(serverId, async () => {
      const updated = await mediaServerApi.regenerateWebhook(serverId);
      setServers((prev) => replaceServer(prev, updated));
      toast.success('Webhook URL regenerated');
    });

  const testWebhook = (serverId: number) =>
    runWebhookAction(
      serverId,
      async () => {
        const result = await mediaServerApi.testWebhook(serverId, true);
        if (result.libraries.length === 0) {
          toast.info('Test received — but no enabled libraries to pick up. Check the app log.', {
            title: 'Webhook test',
          });
          return;
        }
        const summary = result.libraries.map((l) => `${l.name} (${l.action})`).join(', ');
        toast.success(`Test received. Would pick up: ${summary}. Check the app log.`, {
          title: 'Webhook test',
        });
      },
      'Webhook test'
    );

  const deleteServer = async (serverId: number) => {
    setIsDeleting(true);
    try {
      await mediaServerApi.delete(serverId);
      await reload();
      onServersChanged?.();
      return true;
    } catch (error) {
      reportError(error, 'Delete server', 'Failed to delete server');
      return false;
    } finally {
      setIsDeleting(false);
    }
  };

  const deleteLibrary = async (serverId: number, libraryId: number) => {
    setIsDeleting(true);
    try {
      await libraryApi.deleteLibrary(serverId, libraryId);
      await reload();
      onServersChanged?.();
      return true;
    } catch (error) {
      reportError(error, 'Delete library', 'Failed to delete library');
      return false;
    } finally {
      setIsDeleting(false);
    }
  };

  const loadAvailableLibraries = async (serverId: number) => {
    setAvailableLibraries([]);
    setIsLoadingAvailable(true);
    try {
      setAvailableLibraries(await mediaServerApi.getAvailableLibraries(serverId));
    } catch (error) {
      reportError(error, 'Add libraries', 'Failed to fetch available libraries');
    } finally {
      setIsLoadingAvailable(false);
    }
  };

  const addLibraries = async (serverId: number, libraries: MediaServerLibrary[],
                             defaults: NewLibraryDefaults = {}) => {
    if (libraries.length === 0) return false;

    setIsAddingLibraries(true);
    try {
      await mediaServerApi.addLibraries(serverId, libraries, defaults);
      await reload();
      onServersChanged?.();
      return true;
    } catch (error) {
      reportError(error, 'Add libraries', 'Failed to add libraries');
      return false;
    } finally {
      setIsAddingLibraries(false);
    }
  };

  const serverCreated = async () => {
    await reload();
    onServersChanged?.();
  };

  return {
    servers,
    dirtyLibraries,
    dirtyServers,
    isSaving,
    isDeleting,
    webhookBusy,
    tokenBusy,
    availableLibraries,
    isLoadingAvailable,
    isAddingLibraries,
    changeLibrarySettings,
    changeLanguageOrder,
    changePosterFallback,
    saveServer,
    updateToken,
    toggleWebhook,
    regenerateWebhook,
    testWebhook,
    deleteServer,
    deleteLibrary,
    loadAvailableLibraries,
    addLibraries,
    serverCreated,
  };
}
