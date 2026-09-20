import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { WelcomePage } from './WelcomePage';
import { configApi, libraryApi, mediaServerApi } from '../api';
import type { Library, MediaServerResponse } from '../types';

const auth = vi.hoisted(() => ({ isAdmin: true }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => auth }));

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  mediaServerApi: { testPlex: vi.fn(), testJellyfin: vi.fn(), create: vi.fn() },
  configApi: { findConfigs: vi.fn(), createConfig: vi.fn() },
  serviceApi: { testProvider: vi.fn() },
  libraryApi: {
    syncLibraryPosters: vi.fn(),
    syncLibrary: vi.fn(),
    getLibrarySettings: vi.fn(() => Promise.resolve({ upload_enabled: true })),
  },
}));

const SERVER = { id: 4, name: 'Living room', type: 'PLEX' } as MediaServerResponse;
const FILMS = { id: 9, media_server_id: 4, name: 'Films', library_type: 'movie' } as Library;

function renderPage(mediaServers: { server: MediaServerResponse; libraries: Library[] }[] = []) {
  const onDataChanged = vi.fn();
  const onOpenLibrary = vi.fn();
  render(
    <MemoryRouter>
      <WelcomePage mediaServers={mediaServers} onDataChanged={onDataChanged} onOpenLibrary={onOpenLibrary} />
    </MemoryRouter>
  );
  return { onDataChanged, onOpenLibrary };
}

beforeEach(() => {
  vi.clearAllMocks();
  auth.isAdmin = true;
  vi.mocked(configApi.findConfigs).mockResolvedValue([]);
});

describe('WelcomePage', () => {
  it('tells a non-admin who can set things up, instead of showing forms', () => {
    auth.isAdmin = false;
    renderPage();

    expect(screen.getByText(/Only an admin can connect one/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Connect' })).not.toBeInTheDocument();
  });

  it('connects a server and adds the libraries it found', async () => {
    vi.mocked(mediaServerApi.testPlex).mockResolvedValue({
      name: 'Living room',
      libraries: [{ id: 'a', name: 'Films', type: 'movie', item_count: 1204, language: 'en' }],
    });
    vi.mocked(mediaServerApi.create).mockResolvedValue(SERVER);
    const user = userEvent.setup();
    const { onDataChanged } = renderPage();

    await user.type(screen.getByLabelText('Plex token'), 'secret');
    await user.click(screen.getByRole('button', { name: 'Connect' }));
    await user.click(await screen.findByRole('button', { name: 'Add server and 1 library' }));

    expect(mediaServerApi.create).toHaveBeenCalledWith(expect.objectContaining({
      name: 'Living room', type: 'PLEX', token: 'secret',
      libraries: [expect.objectContaining({ id: 'a' })],
    }));
    expect(onDataChanged).toHaveBeenCalled();
  });

  it('turns TVmaze on when continuing, and warns what skipping TMDB costs a film library', async () => {
    const user = userEvent.setup();
    renderPage([{ server: SERVER, libraries: [FILMS] }]);

    expect(await screen.findByText(/Without TMDB, Films will get few posters/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Continue' }));

    expect(configApi.createConfig).toHaveBeenCalledWith(expect.objectContaining({ name: 'tvmaze', enabled: true }));
    expect(await screen.findByRole('button', { name: 'Generate posters' })).toBeInTheDocument();
  });

  it('starts the run and opens the library that shows it', async () => {
    vi.mocked(libraryApi.syncLibraryPosters).mockResolvedValue({ task_id: 't' } as never);
    const user = userEvent.setup();
    const { onOpenLibrary } = renderPage([{ server: SERVER, libraries: [FILMS] }]);
    await user.click(await screen.findByRole('button', { name: 'Continue' }));

    expect(await screen.findByText(/Films uploads new posters to your media server/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Generate posters' }));

    await waitFor(() => expect(onOpenLibrary).toHaveBeenCalledWith(4, 9));
    expect(libraryApi.syncLibraryPosters).toHaveBeenCalledWith(4, 9);
  });
});
