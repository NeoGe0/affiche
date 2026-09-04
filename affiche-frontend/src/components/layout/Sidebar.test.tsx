import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { Sidebar } from './Sidebar';
import type { Library, MediaServerResponse } from '../../types';

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ username: 'boss', isAdmin: true, logout: vi.fn() }),
}));

vi.mock('../../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api')>()),
  settingsApi: { getSettingsInfo: () => Promise.resolve({ version: '0.1.0-beta.1' }) },
}));

const server = (id: number, name: string) =>
  ({ id, name, type: 'PLEX', url: 'http://x', enabled: true }) as MediaServerResponse;

const library = (id: number, mediaServerId: number, name: string) =>
  ({ id, media_server_id: mediaServerId, name, library_type: 'movie' }) as Library;

const MEDIA_SERVERS = [
  { server: server(1, 'Ubuntu'), libraries: [library(10, 1, 'Films')] },
  { server: server(2, 'Attic'), libraries: [library(20, 2, 'Docs')] },
];

function renderSidebar(selectedMediaServerId?: number) {
  const ui = (id?: number) => (
    <MemoryRouter>
      <Sidebar
        mediaServers={MEDIA_SERVERS}
        selectedMediaServerId={id}
        onSelectLibrary={vi.fn()}
        onSelectCollections={vi.fn()}
        onSelectTrash={vi.fn()}
        onOpenSearch={vi.fn()}
      />
    </MemoryRouter>
  );
  const utils = render(ui(selectedMediaServerId));
  return { ...utils, rerenderWith: (id?: number) => utils.rerender(ui(id)) };
}

const filmsVisible = () => screen.queryByText('Films') !== null;
const docsVisible = () => screen.queryByText('Docs') !== null;

describe('Sidebar version', () => {
  it('shows the running version, flagged as a beta while it is a pre-release', async () => {
    renderSidebar(1);

    expect(await screen.findByText('v0.1.0-beta.1')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
  });
});

describe('Sidebar server expansion', () => {
  it('leaves servers collapsed when none is selected', () => {
    renderSidebar(undefined);

    expect(filmsVisible()).toBe(false);
    expect(docsVisible()).toBe(false);
  });

  it('auto-expands a server once it becomes the selected one', () => {
    const { rerenderWith } = renderSidebar(undefined);
    expect(filmsVisible()).toBe(false);

    rerenderWith(1);

    expect(filmsVisible()).toBe(true);
  });

  it('auto-expands a server that is already selected on first render', () => {

    renderSidebar(1);

    expect(filmsVisible()).toBe(true);
  });

  it('keeps a manually collapsed server collapsed across re-renders', async () => {

    const user = userEvent.setup();
    const { rerenderWith } = renderSidebar(1);
    expect(filmsVisible()).toBe(true);

    await user.click(screen.getByText('Ubuntu'));
    expect(filmsVisible()).toBe(false);

    rerenderWith(1);

    expect(filmsVisible()).toBe(false);
  });

  it('expands a newly selected server without re-expanding a collapsed one', async () => {
    const user = userEvent.setup();
    const { rerenderWith } = renderSidebar(1);
    await user.click(screen.getByText('Ubuntu'));
    expect(filmsVisible()).toBe(false);

    rerenderWith(2);

    expect(docsVisible()).toBe(true);
    expect(filmsVisible()).toBe(false);
  });
});
