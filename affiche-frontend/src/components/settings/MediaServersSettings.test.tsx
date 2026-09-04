import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { MediaServersSettings } from './MediaServersSettings';
import { ToastProvider } from '../../context/ToastContext';
import { libraryApi, mediaServerApi, settingsApi } from '../../api';
import type {
  AppSettings, Library, LibrarySettings, MediaServerResponse,
} from '../../types';

vi.mock('../../api', () => ({
  mediaServerApi: {
    getAll: vi.fn(),
    delete: vi.fn(),
    setWebhook: vi.fn(),
    regenerateWebhook: vi.fn(),
    testWebhook: vi.fn(),
    getAvailableLibraries: vi.fn(),
    addLibraries: vi.fn(),
    setLanguageOrder: vi.fn(),
    setPosterFallback: vi.fn(),
    updateToken: vi.fn(),
  },
  libraryApi: {
    getLibraries: vi.fn(),
    getLibrarySettings: vi.fn(),
    updateLibrarySettings: vi.fn(),
    deleteLibrary: vi.fn(),
  },

  settingsApi: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
  },

  errorMessage: (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback,
}));

const server: MediaServerResponse = {
  id: 1,
  name: 'Home Plex',
  type: 'PLEX',
  url: 'http://localhost:32400',
  enabled: true,
  language_order: ['', 'en', 'fr'],
  fallback_to_server_poster: false,
  skip_style_when_not_textless: false,
  webhook_enabled: false,
  webhook_token: null,
  last_sync: null,
  created_at: '',
  updated_at: '',
};

const movies = { id: 10, media_server_id: 1, name: 'Movies', library_type: 'movie', media_count: 42 } as Library;
const shows = { id: 11, media_server_id: 1, name: 'Shows', library_type: 'show', media_count: 7 } as Library;

const settingsFor = (libraryId: number): LibrarySettings => ({
  library_id: libraryId,
  enabled: true,
  upload_enabled: true,
  provider_order: ['tmdb', 'tvdb', 'fanart'],
  track_episodes: false, track_collections: false,
  auto_sync_enabled: false,
  auto_sync_interval_minutes: 360,
  auto_pickup_action: 'sync',
  last_auto_sync_at: null,
  last_full_sync_at: null,
});

const getAll = vi.mocked(mediaServerApi.getAll);
const deleteServer = vi.mocked(mediaServerApi.delete);
const getLibraries = vi.mocked(libraryApi.getLibraries);
const getLibrarySettings = vi.mocked(libraryApi.getLibrarySettings);
const updateLibrarySettings = vi.mocked(libraryApi.updateLibrarySettings);
const setLanguageOrder = vi.mocked(mediaServerApi.setLanguageOrder);
const setPosterFallback = vi.mocked(mediaServerApi.setPosterFallback);
const updateToken = vi.mocked(mediaServerApi.updateToken);
const getSettings = vi.mocked(settingsApi.getSettings);

const appSettings = {
  trash_retention_days: 30,
  log_level: 'INFO',
  new_library_provider_order: ['tmdb'],
  new_library_enabled: true,
  new_library_upload_enabled: true,
} as AppSettings;

beforeEach(() => {
  vi.resetAllMocks();
  getAll.mockResolvedValue([server]);
  getLibraries.mockResolvedValue([movies, shows]);
  getLibrarySettings.mockImplementation(async (_serverId, libraryId) => settingsFor(libraryId));

  setLanguageOrder.mockResolvedValue(server);
  setPosterFallback.mockResolvedValue(server);
  getSettings.mockResolvedValue(appSettings);
});

const renderScreen = () =>
  render(
    <ToastProvider>
      <MediaServersSettings />
    </ToastProvider>
  );

const openServerSettings = async (user = userEvent.setup()) => {
  await user.click(await screen.findByRole('button', { name: 'Server settings' }));
  return user;
};

const openLibraries = async (user = userEvent.setup()) => {
  await user.click(await screen.findByRole('button', { name: /^Libraries/ }));
  return user;
};

const openMoviesSettings = async () => {
  renderScreen();
  const user = await openLibraries();

  await user.click(screen.getByRole('button', { name: /Movies/ }));

  return user;
};

describe('MediaServersSettings card expansion', () => {
  it('opens the first server without a click, so its libraries are one click away', async () => {
    renderScreen();
    await openLibraries();

    expect(screen.getByRole('button', { name: /Movies/ })).toBeInTheDocument();
  });

  it('lets that first server be closed again', async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(await screen.findByRole('button', { name: /Home Plex/ }));

    expect(screen.queryByRole('button', { name: /Movies/ })).not.toBeInTheDocument();
  });
});

describe('MediaServersSettings loading', () => {
  it('fetches the settings of every library of every server', async () => {
    renderScreen();

    await waitFor(() => expect(getLibrarySettings).toHaveBeenCalledTimes(2));
    expect(getLibrarySettings).toHaveBeenCalledWith(1, 10);
    expect(getLibrarySettings).toHaveBeenCalledWith(1, 11);
  });

  it('reports a failure to list the servers', async () => {
    getAll.mockRejectedValue(new Error('Backend unreachable'));

    renderScreen();

    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unreachable');
  });

  it('still renders a library whose settings row does not exist yet', async () => {
    getLibrarySettings.mockRejectedValue(new Error('404'));
    const user = await openMoviesSettings();

    const enabled = screen.getByRole('checkbox', { name: 'Enabled' });
    expect(enabled).toBeChecked();

    await user.click(enabled);
    expect(enabled).not.toBeChecked();
  });
});

describe('MediaServersSettings saving', () => {
  it('sends only the editable fields, not the server-owned ones', async () => {
    updateLibrarySettings.mockResolvedValue(settingsFor(10));
    const user = await openMoviesSettings();

    await user.click(screen.getByRole('checkbox', { name: 'Enabled' }));
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    await waitFor(() => expect(updateLibrarySettings).toHaveBeenCalledTimes(1));
    const [serverId, libraryId, body] = updateLibrarySettings.mock.calls[0];
    expect(serverId).toBe(1);
    expect(libraryId).toBe(10);
    expect(body).toEqual({
      enabled: false,
      upload_enabled: true,
      provider_order: ['tmdb', 'tvdb', 'fanart'],
      track_episodes: false,
      track_collections: false,
      auto_sync_enabled: false,
      auto_sync_interval_minutes: 360,
      auto_pickup_action: 'sync',
      overlay_options: null,
      text_options: null,
      style_profile_id: null,
    });
  });

  it('clears the unsaved marker once the save lands', async () => {
    updateLibrarySettings.mockResolvedValue(settingsFor(10));
    const user = await openMoviesSettings();

    await user.click(screen.getByRole('checkbox', { name: 'Enabled' }));
    expect(screen.getByText('Unsaved')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    await waitFor(() => expect(screen.queryByText('Unsaved')).not.toBeInTheDocument());
  });

  it('keeps the edit marked unsaved and says why when the save fails', async () => {
    updateLibrarySettings.mockRejectedValue(new Error('Library is locked'));
    const user = await openMoviesSettings();

    await user.click(screen.getByRole('checkbox', { name: 'Enabled' }));
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Library is locked');
    expect(screen.getByText('Unsaved')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save Changes/ })).toBeEnabled();
  });

  it('saves every dirty library of the card in one go', async () => {
    updateLibrarySettings.mockResolvedValue(settingsFor(10));
    const user = await openMoviesSettings();

    await user.click(screen.getByRole('checkbox', { name: 'Enabled' }));
    await user.click(screen.getByRole('button', { name: /Shows/ }));
    await user.click(screen.getByRole('checkbox', { name: 'Track episodes' }));
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    await waitFor(() => expect(updateLibrarySettings).toHaveBeenCalledTimes(2));
    expect(updateLibrarySettings.mock.calls.map((c) => c[1]).sort()).toEqual([10, 11]);
  });
});

describe('MediaServersSettings deletion', () => {
  const openDeleteServerConfirm = async () => {
    renderScreen();
    const user = await openServerSettings();

    await user.click(screen.getByRole('button', { name: 'More actions' }));
    await user.click(screen.getByRole('menuitem', { name: 'Delete Server' }));

    return user;
  };

  it('keeps the confirmation open and reports the reason when the delete fails', async () => {
    deleteServer.mockRejectedValue(new Error('Server is in use'));
    const user = await openDeleteServerConfirm();

    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Server is in use');
    expect(screen.getByText('Delete Server')).toBeInTheDocument();
  });

  it('closes the confirmation and refreshes once the delete lands', async () => {
    deleteServer.mockResolvedValue(undefined as never);
    const user = await openDeleteServerConfirm();
    getAll.mockResolvedValue([]);

    await user.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() =>
      expect(screen.getByText(/No media servers connected yet/)).toBeInTheDocument()
    );
  });
});

describe('MediaServersSettings artwork languages', () => {
  it('saves a reordered language list with the rest of the card', async () => {
    setLanguageOrder.mockResolvedValue({ ...server, language_order: ['en', '', 'fr'] });
    renderScreen();
    const user = await openServerSettings();

    await user.click(screen.getByRole('button', { name: 'Move English up' }));
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    await waitFor(() => expect(setLanguageOrder).toHaveBeenCalledWith(1, ['en', '', 'fr']));

    expect(updateLibrarySettings).not.toHaveBeenCalled();
  });

  it('keeps the card unsaved and says why when the language save fails', async () => {
    setLanguageOrder.mockRejectedValue(new Error('Server unreachable'));
    renderScreen();
    const user = await openServerSettings();

    await user.click(screen.getByRole('button', { name: 'Move English up' }));
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Server unreachable');
    expect(screen.getByRole('button', { name: /Save Changes/ })).toBeInTheDocument();
  });
});

describe('MediaServersSettings poster fallbacks', () => {
  const openServerCard = async () => {
    renderScreen();
    const user = await openServerSettings();
    await screen.findByRole('checkbox', { name: /Style the media server's own poster/ });
    return user;
  };

  it('saves a toggled fallback with the rest of the card', async () => {
    const updated = { ...server, fallback_to_server_poster: true };
    setPosterFallback.mockResolvedValue(updated);

    const user = await openServerCard();
    await user.click(screen.getByRole('checkbox', { name: /Style the media server's own poster/ }));
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    await waitFor(() =>
      expect(setPosterFallback).toHaveBeenCalledWith(1, {
        fallback_to_server_poster: true,
        skip_style_when_not_textless: false,
      })
    );
  });

  it('sends both checkboxes together, since one endpoint carries the pair', async () => {
    const user = await openServerCard();
    await user.click(
      screen.getByRole('checkbox', { name: /Use posters that already have a title as-is/ })
    );
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    await waitFor(() =>
      expect(setPosterFallback).toHaveBeenCalledWith(1, {
        fallback_to_server_poster: false,
        skip_style_when_not_textless: true,
      })
    );
  });

  it('keeps the card unsaved and says why when the fallback save fails', async () => {
    setPosterFallback.mockRejectedValue(new Error('Server unreachable'));

    const user = await openServerCard();
    await user.click(screen.getByRole('checkbox', { name: /Style the media server's own poster/ }));
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Server unreachable');
    expect(screen.getByRole('button', { name: /Save Changes/ })).toBeInTheDocument();
  });
});

describe('MediaServersSettings webhooks', () => {
  it('shows the inbound URL once the backend mints a token', async () => {
    vi.mocked(mediaServerApi.setWebhook).mockResolvedValue({
      ...server,
      webhook_enabled: true,
      webhook_token: 'tok-123',
    });
    renderScreen();
    const user = await openServerSettings();

    await user.click(screen.getByRole('checkbox', { name: 'Enable webhooks' }));

    const url = await screen.findByText(/\/affiche\/webhooks\/tok-123$/);
    expect(url).toBeInTheDocument();
  });

  it('reports a webhook toggle that fails, leaving the switch off', async () => {
    vi.mocked(mediaServerApi.setWebhook).mockRejectedValue(new Error('Plex Pass required'));
    renderScreen();
    const user = await openServerSettings();

    await user.click(screen.getByRole('checkbox', { name: 'Enable webhooks' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Plex Pass required');
    expect(screen.getByRole('checkbox', { name: 'Enable webhooks' })).not.toBeChecked();
  });
});

describe('MediaServersSettings auto-sync interval', () => {
  it('edits in hours and days while storing minutes', async () => {
    updateLibrarySettings.mockResolvedValue(settingsFor(10));
    const user = await openMoviesSettings();

    await user.click(screen.getByRole('checkbox', { name: 'Scheduled auto-sync' }));

    expect(screen.getByRole('spinbutton', { name: 'Check every' })).toHaveValue(6);

    await user.selectOptions(screen.getByRole('combobox', { name: 'Interval unit' }), 'days');
    await user.click(screen.getByRole('button', { name: /Save Changes/ }));

    await waitFor(() => expect(updateLibrarySettings).toHaveBeenCalled());
    const body = updateLibrarySettings.mock.calls[0][2];
    expect(body.auto_sync_interval_minutes).toBe(6 * 1440);
  });
});

describe('MediaServersSettings card independence', () => {
  it('opens one server at a time', async () => {
    const second: MediaServerResponse = { ...server, id: 2, name: 'Attic Jellyfin', type: 'JELLYFIN' };
    getAll.mockResolvedValue([server, second]);
    getLibraries.mockResolvedValue([]);
    renderScreen();
    const user = await openServerSettings();

    expect(screen.getByRole('checkbox', { name: 'Enable webhooks' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Attic Jellyfin/ }));
    await openServerSettings(user);

    expect(screen.getAllByRole('checkbox', { name: 'Enable webhooks' })).toHaveLength(1);
    expect(screen.getByText(/Jellyfin Webhook plugin/)).toBeInTheDocument();
  });
});

describe('MediaServersSettings token update', () => {

  const tokenField = () => screen.getByLabelText('New api token');

  it('sends what was typed and empties the field once it lands', async () => {
    updateToken.mockResolvedValue(server);
    renderScreen();
    const user = await openServerSettings();

    await user.type(screen.getByLabelText('New api token'), 'fresh-plex-token');
    await user.click(screen.getByRole('button', { name: 'Update' }));

    await waitFor(() => expect(updateToken).toHaveBeenCalledWith(1, 'fresh-plex-token'));
    await waitFor(() => expect(tokenField()).toHaveValue(''));
  });

  it('keeps what was typed and says why when the server rejects it', async () => {
    updateToken.mockRejectedValue(new Error('Plex rejected that token'));
    renderScreen();
    const user = await openServerSettings();

    await user.type(screen.getByLabelText('New api token'), 'typo-token');
    await user.click(screen.getByRole('button', { name: 'Update' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Plex rejected that token');

    expect(tokenField()).toHaveValue('typo-token');
  });

  it('starts empty, because the stored token is never sent to the browser', async () => {
    renderScreen();
    await openServerSettings();

    expect(screen.getByLabelText('New api token')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Update' })).toBeDisabled();
  });

  it('does not submit whitespace', async () => {
    renderScreen();
    const user = await openServerSettings();

    await user.type(screen.getByLabelText('New api token'), '   ');

    expect(screen.getByRole('button', { name: 'Update' })).toBeDisabled();
    expect(updateToken).not.toHaveBeenCalled();
  });
});
