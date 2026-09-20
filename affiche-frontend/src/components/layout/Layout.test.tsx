import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { Layout } from './Layout';

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ username: 'boss', isAdmin: true, logout: vi.fn() }),
}));

vi.mock('../../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api')>()),
  settingsApi: { getSettingsInfo: () => Promise.resolve({ version: '1.0.0' }) },
}));

vi.mock('../search', () => ({ GlobalSearchModal: () => null }));

function pretendWindowIsNarrow(narrow: boolean) {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: narrow && query.includes('max-width'),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
}

afterEach(() => vi.unstubAllGlobals());

function renderLayout() {
  render(
    <MemoryRouter>
      <Layout
        mediaServers={[]}
        onSelectLibrary={vi.fn()}
        onSelectTrash={vi.fn()}
        onSelectCollections={vi.fn()}
        onOpenSearchHit={vi.fn()}
      >
        <p>Page</p>
      </Layout>
    </MemoryRouter>
  );
}

const openFromRail = async (user: ReturnType<typeof userEvent.setup>) =>
  user.click(screen.getAllByRole('button', { name: 'Expand menu' })[0]);

describe('Layout in a narrow window', () => {
  it('shows only the rail until the menu is opened', () => {
    pretendWindowIsNarrow(true);
    renderLayout();

    expect(screen.getAllByRole('button', { name: 'Expand menu' }).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument();
  });

  it('closes the open menu on Escape', async () => {
    pretendWindowIsNarrow(true);
    const user = userEvent.setup();
    renderLayout();

    await openFromRail(user);
    expect(screen.getByRole('button', { name: 'Close menu' })).toBeInTheDocument();

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument();
  });

  it('closes the open menu once something in it is picked', async () => {
    pretendWindowIsNarrow(true);
    const user = userEvent.setup();
    renderLayout();

    await openFromRail(user);

    await user.click(screen.getByText('Dashboard'));

    expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument();
  });
});

describe('Layout in a wide window', () => {
  it('collapses to the rail and back, with no overlay involved', async () => {
    pretendWindowIsNarrow(false);
    const user = userEvent.setup();
    renderLayout();

    await user.click(screen.getByRole('button', { name: 'Collapse menu' }));
    await openFromRail(user);

    expect(screen.getByRole('button', { name: 'Collapse menu' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument();
  });
});
