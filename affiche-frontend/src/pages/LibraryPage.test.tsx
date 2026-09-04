import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { LibraryPage } from './LibraryPage';
import { libraryApi, tasksApi } from '../api';
import type { Library, LibraryItem } from '../types';

vi.mock('../api', () => ({
  libraryApi: {
    getLibraryItems: vi.fn(),
    getTrashItems: vi.fn(),
    getLibraryAlphaIndex: vi.fn(),
    getLibraryItemCounts: vi.fn(),
    getItemPosterUrl: (libraryId: number, itemId: number, version?: string | null) =>
      `/affiche/libraries/${libraryId}/items/${itemId}/poster${version ? `?v=${version}` : ''}`,

    syncLibrary: vi.fn(),
    syncAllLibraries: vi.fn(),
    syncLibraryPosters: vi.fn(),
    syncAllPosters: vi.fn(),
    uploadLibraryPosters: vi.fn(),
    uploadAllPosters: vi.fn(),
    resetLibraryPosters: vi.fn(),
    resetAllPosters: vi.fn(),
    emptyTrash: vi.fn(),
    restoreItem: vi.fn(),

    syncItem: vi.fn(),
    syncItemPosters: vi.fn(),
    resetItemPosters: vi.fn(),
    uploadItemPoster: vi.fn(),
    getItemWithSeasons: vi.fn(),
    getItem: vi.fn(),
  },
  tasksApi: {
    getRunningBlockingTask: vi.fn(),
    cancelTask: vi.fn(),
  },
  postersApi: {},

  errorMessage: (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback,
}));

const toast = { error: vi.fn(), success: vi.fn(), info: vi.fn(), show: vi.fn() };
vi.mock('../context/ToastContext', () => ({
  useToast: () => toast,
}));

type StreamHandlers = NonNullable<Parameters<typeof import('../hooks').useEventStream>[0]>;
let handlers: StreamHandlers = {};

vi.mock('../hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../hooks')>()),
  useEventStream: (options: StreamHandlers) => {
    handlers = options;
  },
}));

import { installIntersectionObserver } from '../test/intersectionObserver';

const MOVIES: Library = { id: 2, media_server_id: 1, name: 'Movies', library_type: 'movie' };
const SHOWS: Library = { id: 3, media_server_id: 1, name: 'Shows', library_type: 'show' };

function item(overrides: Partial<LibraryItem> & { id: number; title: string }): LibraryItem {
  return { library_id: 2, type: 'movie', processed: false, locked: false, has_poster: false, ...overrides };
}

const getLibraryItems = vi.mocked(libraryApi.getLibraryItems);
const getRunningBlockingTask = vi.mocked(tasksApi.getRunningBlockingTask);

const page = (items: LibraryItem[], total = items.length) => ({
  items,
  total,
  total_pages: Math.ceil(total / 50),
  page: 0,
  page_size: 50,
});

type PageProps = Partial<React.ComponentProps<typeof LibraryPage>>;

const pageElement = (props: PageProps) => (
  <MemoryRouter>
    <LibraryPage
      mediaServerId={1}
      mediaServerName="Plex"
      libraries={[MOVIES]}
      allLibraries={[MOVIES]}
      selectedLibraryId={2}
      onRefreshLibraries={vi.fn()}
      {...props}
    />
  </MemoryRouter>
);

function renderPage(props: PageProps = {}) {
  const onRefreshLibraries = props.onRefreshLibraries ?? vi.fn();
  const utils = render(pageElement({ ...props, onRefreshLibraries }));
  return { ...utils, onRefreshLibraries };
}

const poster = (title: string) => screen.queryByAltText(title) as HTMLImageElement | null;
const stopButton = () => screen.queryByTitle('Stop current task');

beforeEach(() => {
  installIntersectionObserver();
  handlers = {};
  toast.error.mockReset();
  getLibraryItems.mockResolvedValue(page([item({ id: 10, title: 'Alien' })]));
  vi.mocked(libraryApi.getLibraryAlphaIndex).mockResolvedValue([]);
  vi.mocked(libraryApi.getLibraryItemCounts).mockResolvedValue({ total: 0, unprocessed: 0, errors: 0, locked: 0, providers: {} });
  getRunningBlockingTask.mockResolvedValue(null);
});

afterEach(() => {
  vi.mocked(libraryApi.getLibraryItems).mockReset();
});

describe('LibraryPage — live poster updates', () => {
  it('reveals a poster on item_processed even though the item loaded with none', async () => {

    renderPage();
    await screen.findByText('Alien');
    expect(poster('Alien')).toBeNull();

    act(() => handlers.onItemProcessed?.(2, 10, true, '1a2b-3c'));

    expect(poster('Alien')?.getAttribute('src')).toBe(
      '/affiche/libraries/2/items/10/poster?v=1a2b-3c'
    );
  });

  it('follows the server version on every subsequent event for the same item', async () => {

    renderPage();
    await screen.findByText('Alien');

    act(() => handlers.onItemProcessed?.(2, 10, true, '1a2b-3c'));
    act(() => handlers.onItemProcessed?.(2, 10, true, '9f8e-4d'));

    expect(poster('Alien')?.getAttribute('src')).toContain('?v=9f8e-4d');
  });

  it('keeps concurrent updates for different items from clobbering each other', async () => {

    getLibraryItems.mockResolvedValue(
      page([item({ id: 10, title: 'Alien' }), item({ id: 11, title: 'Blade Runner' })])
    );
    renderPage();
    await screen.findByText('Blade Runner');

    act(() => {
      handlers.onItemProcessed?.(2, 10, true, '1a2b-3c');
      handlers.onItemProcessed?.(2, 11, true, '5e6f-7a');
    });

    expect(poster('Alien')).not.toBeNull();
    expect(poster('Blade Runner')).not.toBeNull();
  });

  it('ignores an event addressed to a different library', async () => {
    renderPage();
    await screen.findByText('Alien');

    act(() => handlers.onItemProcessed?.(99, 10, true, '1a2b-3c'));

    expect(poster('Alien')).toBeNull();
  });
});

describe('LibraryPage — task tracking', () => {
  it('re-attaches to a task already running when the page mounts', async () => {
    getRunningBlockingTask.mockResolvedValue({
      task_id: 'task-1',
      status: 'running',
      task_name: 'poster_upload_2',
      message: 'Uploading posters...',
      progress: { current: 3, total: 10, message: 'Uploading posters...' },
    } as Awaited<ReturnType<typeof tasksApi.getRunningBlockingTask>>);

    renderPage();

    expect(await screen.findByText('Uploading posters...')).toBeInTheDocument();
    expect(stopButton()).toBeInTheDocument();
  });

  it('clears the task and refreshes once it completes', async () => {
    getRunningBlockingTask.mockResolvedValue({
      task_id: 'task-1',
      status: 'running',
      task_name: 'poster_upload_2',
      message: 'Uploading posters...',
    } as Awaited<ReturnType<typeof tasksApi.getRunningBlockingTask>>);
    const { onRefreshLibraries } = renderPage();
    await screen.findByText('Uploading posters...');
    getLibraryItems.mockClear();

    act(() => handlers.onTaskStatus?.('task-1', 'completed', 'poster_upload_2'));

    await waitFor(() => expect(stopButton()).not.toBeInTheDocument());
    expect(onRefreshLibraries).toHaveBeenCalled();
    expect(getLibraryItems).toHaveBeenCalled();
  });

  it('ignores status for a task it is not tracking', async () => {
    getRunningBlockingTask.mockResolvedValue({
      task_id: 'task-1',
      status: 'running',
      task_name: 'poster_upload_2',
      message: 'Uploading posters...',
    } as Awaited<ReturnType<typeof tasksApi.getRunningBlockingTask>>);
    renderPage();
    await screen.findByText('Uploading posters...');

    act(() => handlers.onTaskStatus?.('someone-elses-task', 'completed', 'poster_upload_2'));

    expect(stopButton()).toBeInTheDocument();
  });
});

describe('LibraryPage — listing', () => {
  it('gives every library its own row on the server home', async () => {

    getLibraryItems.mockImplementation((_ms: number, libraryId: number) =>
      Promise.resolve(
        libraryId === 2
          ? page([item({ id: 10, title: 'Alien', added_at: '2026-01-02T00:00:00Z' })], 40)
          : page([item({ id: 20, title: 'Fringe', library_id: 3, added_at: '2026-01-01T00:00:00Z' })], 2)
      )
    );

    renderPage({ libraries: [MOVIES, SHOWS], allLibraries: [MOVIES, SHOWS], selectedLibraryId: undefined });

    expect(await screen.findByRole('button', { name: /^Movies/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Shows/ })).toBeInTheDocument();

    expect(screen.getAllByText('Alien')).toHaveLength(1);
    expect(screen.getAllByText('Fringe')).toHaveLength(1);

    expect(screen.getByRole('heading', { name: /Home/ })).toBeInTheDocument();
  });

  it('asks each library only for the newest page, not for a listing behind the rows', async () => {
    renderPage({ libraries: [MOVIES, SHOWS], allLibraries: [MOVIES, SHOWS], selectedLibraryId: undefined });

    await screen.findByRole('button', { name: /^Movies/ });
    for (const call of getLibraryItems.mock.calls) {
      expect(call[2]).toMatchObject({ page: 0, sortBy: 'added_at', sortDir: 'desc' });
    }
  });

  it('refetches when a library_synced event names the current media server', async () => {
    renderPage();
    await screen.findByText('Alien');
    getLibraryItems.mockClear();
    getLibraryItems.mockResolvedValue(
      page([item({ id: 10, title: 'Alien' }), item({ id: 12, title: 'Arrival' })])
    );

    act(() => handlers.onLibrarySynced?.(1, 2));

    expect(await screen.findByText('Arrival')).toBeInTheDocument();
  });

  it('ignores a sync from another media server', async () => {
    renderPage();
    await screen.findByText('Alien');
    getLibraryItems.mockClear();

    act(() => handlers.onLibrarySynced?.(99, null));

    expect(getLibraryItems).not.toHaveBeenCalled();
  });

  it('shows the library name and its items', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: /Plex.*Movies/ })).toBeInTheDocument();
    expect(screen.getByText('Alien')).toBeInTheDocument();
  });
});

describe('LibraryPage — filter counts', () => {
  const getCounts = vi.mocked(libraryApi.getLibraryItemCounts);

  const openFilters = async () => {
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /Filters/ }));
    return user;
  };

  const filterRow = (name: RegExp) => screen.findByRole('radio', { name });

  it('labels each filter with the number of items behind it', async () => {
    getCounts.mockResolvedValue({ total: 1234, unprocessed: 57, errors: 3, locked: 0, providers: {} });

    renderPage();
    await openFilters();

    expect(await filterRow(/^All items 1,234$/)).toBeInTheDocument();
    expect(await filterRow(/^Unprocessed 57$/)).toBeInTheDocument();
    expect(await filterRow(/^With errors 3$/)).toBeInTheDocument();
  });

  it('offers no filter controls on the home, which steers no listing', async () => {
    getCounts.mockClear();
    renderPage({ libraries: [MOVIES, SHOWS], allLibraries: [MOVIES, SHOWS], selectedLibraryId: undefined });

    await screen.findByRole('button', { name: /^Movies/ });
    expect(screen.queryByRole('button', { name: /filter/i })).not.toBeInTheDocument();
    expect(getCounts).not.toHaveBeenCalled();
  });

  it('keeps the labels bare rather than showing a number it could not fetch', async () => {
    getCounts.mockRejectedValue(new Error('500'));

    renderPage();
    await openFilters();

    expect(await filterRow(/^All items$/)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'With errors' })).toBeInTheDocument();
  });

  it('offers a provider bucket per provenance the library holds', async () => {
    getCounts.mockResolvedValue({
      total: 6, unprocessed: 0, errors: 0, locked: 0,
      providers: { tmdb: 4, mediux: 1, none: 1 },
    });

    renderPage();
    await openFilters();

    expect(await filterRow(/^Any source 6$/)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'TMDB 4' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'No source recorded 1' })).toBeInTheDocument();

    expect(screen.queryByRole('radio', { name: /Fanart/ })).not.toBeInTheDocument();
  });

  it('filters the listing by provider without disturbing the status filter', async () => {

    getCounts.mockResolvedValue({
      total: 6, unprocessed: 2, errors: 0, locked: 0, providers: { tmdb: 4, mediux: 2 },
    });
    renderPage();
    await screen.findByText('Alien');
    const user = await openFilters();

    await user.click(await filterRow(/^MediUX/));
    await user.click(await filterRow(/^Unprocessed/));

    await waitFor(() => {
      expect(getLibraryItems).toHaveBeenLastCalledWith(
        1, 2, expect.objectContaining({ provider: 'mediux', status: 'unprocessed' })
      );
    });
  });

  it('names both narrowings outside the panel, so a short grid is never a mystery', async () => {
    getCounts.mockResolvedValue({
      total: 6, unprocessed: 2, errors: 0, locked: 0, providers: { mediux: 2 },
    });
    renderPage();
    await screen.findByText('Alien');
    const user = await openFilters();
    await user.click(await filterRow(/^MediUX/));
    await user.click(await filterRow(/^Unprocessed/));

    await user.keyboard('{Escape}');

    expect(screen.getByTitle('Remove the Unprocessed filter')).toBeInTheDocument();
    expect(screen.getByTitle('Remove the MediUX filter')).toBeInTheDocument();
  });

  it('drops a narrowing when its chip is clicked, leaving the other one alone', async () => {
    getCounts.mockResolvedValue({
      total: 6, unprocessed: 2, errors: 0, locked: 0, providers: { mediux: 2 },
    });
    renderPage();
    await screen.findByText('Alien');
    const user = await openFilters();
    await user.click(await filterRow(/^MediUX/));
    await user.click(await filterRow(/^Unprocessed/));
    await user.keyboard('{Escape}');

    await user.click(screen.getByTitle('Remove the MediUX filter'));

    await waitFor(() => {
      expect(getLibraryItems).toHaveBeenLastCalledWith(
        1, 2, expect.objectContaining({ provider: undefined, status: 'unprocessed' })
      );
    });
  });

  it('re-counts once a task finishes, since generating empties the unprocessed bucket', async () => {

    getRunningBlockingTask.mockResolvedValue({
      task_id: 'task-1',
      status: 'running',
      task_name: 'poster_sync_2',
      message: 'Generating posters...',
    } as Awaited<ReturnType<typeof tasksApi.getRunningBlockingTask>>);
    getCounts.mockResolvedValue({ total: 10, unprocessed: 10, errors: 0, locked: 0, providers: {} });
    renderPage();
    await openFilters();
    await filterRow(/^Unprocessed 10$/);

    getCounts.mockResolvedValue({ total: 10, unprocessed: 0, errors: 2, locked: 0, providers: {} });
    act(() => handlers.onTaskStatus?.('task-1', 'completed', 'poster_sync_2'));

    expect(await filterRow(/^Unprocessed 0$/)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'With errors 2' })).toBeInTheDocument();
  });
});

describe('LibraryPage — actions that fail', () => {

  const runHeaderAction = async (button: string | RegExp, confirmLabel: string) => {
    const user = userEvent.setup();
    const utils = renderPage();
    await screen.findByText('Alien');

    await user.click(screen.getByRole('button', { name: button }));
    await user.click(await screen.findByRole('button', { name: confirmLabel }));

    return utils;
  };

  const runMenuAction = async (item: string | RegExp, confirmLabel: string) => {
    const user = userEvent.setup();
    const utils = renderPage();
    await screen.findByText('Alien');

    await user.click(screen.getByRole('button', { name: 'Library actions' }));
    await user.click(await screen.findByRole('menuitem', { name: item }));
    await user.click(await screen.findByRole('button', { name: confirmLabel }));

    return utils;
  };

  it('reports a library sync the backend refused, instead of going quiet', async () => {
    vi.mocked(libraryApi.syncLibrary).mockRejectedValue(new Error('Plex is unreachable'));

    await runMenuAction(/Sync library/, 'Sync');

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Plex is unreachable', { title: 'Sync failed' })
    );
  });

  it('does not leave the header looking like a task is running', async () => {
    vi.mocked(libraryApi.syncLibrary).mockRejectedValue(new Error('nope'));

    await runMenuAction(/Sync library/, 'Sync');

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(stopButton()).toBeNull();
  });

  it('reports a generation that never started', async () => {
    vi.mocked(libraryApi.syncLibraryPosters).mockRejectedValue(new Error('No provider configured'));

    await runHeaderAction(/Generate Posters/, 'Generate');

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('No provider configured', {
        title: 'Generation failed',
      })
    );
  });

  it('falls back to a readable sentence when the rejection carries no message', async () => {
    vi.mocked(libraryApi.syncLibrary).mockRejectedValue('boom');

    await runMenuAction(/Sync library/, 'Sync');

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Could not start the library sync.', {
        title: 'Sync failed',
      })
    );
  });

  it('reports a failed poster generation on the open item', async () => {
    vi.mocked(libraryApi.syncItemPosters).mockRejectedValue(new Error('Poster source is down'));
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText('Alien'));
    await user.click(await screen.findByRole('button', { name: /Generate Poster/ }));
    await user.click(await screen.findByRole('button', { name: 'Generate' }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Poster source is down', {
        title: 'Generation failed',
      })
    );
  });
});

describe('LibraryPage — returning from an item', () => {
  const atScrollY = (y: number) =>
    Object.defineProperty(window, 'scrollY', { value: y, configurable: true });

  it('puts the listing back where the user left it', async () => {

    const scrollTo = vi.fn();
    window.scrollTo = scrollTo as unknown as typeof window.scrollTo;
    atScrollY(1200);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText('Alien'));
    atScrollY(0);
    await user.click(await screen.findByRole('button', { name: /back to library/i }));

    await screen.findByText('Alien');
    expect(scrollTo).toHaveBeenCalledWith(0, 1200);
  });
});

describe('LibraryPage — the item named by the URL', () => {
  const getItem = vi.mocked(libraryApi.getItem);

  it('opens the item the path names, loading the row it does not hold', async () => {

    getItem.mockResolvedValue(item({ id: 42, title: 'Blade Runner' }));
    renderPage({ openItemId: 42 });

    expect(await screen.findByRole('heading', { name: 'Blade Runner' })).toBeInTheDocument();
    expect(getItem).toHaveBeenCalledWith(1, 2, 42);
  });

  it('says so rather than sitting on an empty screen when that item is gone', async () => {
    const onOpenItem = vi.fn();
    getItem.mockRejectedValue(new Error('Item 42 not found'));
    renderPage({ openItemId: 42, onOpenItem });

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Item 42 not found',
      { title: 'Library' }));
    expect(onOpenItem).toHaveBeenCalledWith(null);
  });

  it('navigates when an item is clicked, so the URL names what is on screen', async () => {
    const onOpenItem = vi.fn();
    const user = userEvent.setup();
    renderPage({ onOpenItem });

    await user.click(await screen.findByText('Alien'));

    expect(onOpenItem).toHaveBeenCalledWith(expect.objectContaining({ id: 10 }));
  });

  it('opens the item, not its library, when a home row is clicked', async () => {

    getItem.mockResolvedValue(item({ id: 10, title: 'Alien' }));
    const user = userEvent.setup();
    const { rerender } = renderPage({
      libraries: [MOVIES, SHOWS], allLibraries: [MOVIES, SHOWS], selectedLibraryId: undefined,
    });

    await user.click((await screen.findAllByText('Alien'))[0]);
    rerender(pageElement({
      libraries: [MOVIES, SHOWS], allLibraries: [MOVIES, SHOWS],
      selectedLibraryId: 2, openItemId: 10,
    }));

    expect(await screen.findByRole('heading', { name: 'Alien' })).toBeInTheDocument();
  });

  it('closes the item when the path drops it, as the browser Back button does', async () => {
    getItem.mockResolvedValue(item({ id: 42, title: 'Blade Runner' }));
    const { rerender } = renderPage({ openItemId: 42 });
    await screen.findByRole('heading', { name: 'Blade Runner' });

    rerender(pageElement({ openItemId: undefined }));

    expect(await screen.findByText('Alien')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Blade Runner' })).not.toBeInTheDocument();
  });
});

describe('LibraryPage — emptying the trash', () => {
  const emptyTrash = vi.mocked(libraryApi.emptyTrash);

  const renderTrash = async () => {
    const user = userEvent.setup();
    vi.mocked(libraryApi.getTrashItems).mockResolvedValue(
      page([item({ id: 10, title: 'Alien' })])
    );
    const utils = renderPage({
      mode: 'trash',
      libraries: [MOVIES, SHOWS],
      allLibraries: [MOVIES, SHOWS],
      selectedLibraryId: undefined,
    });

    await screen.findAllByText('Alien');

    await user.click(screen.getByRole('button', { name: 'Empty trash' }));

    const buttons = await screen.findAllByRole('button', { name: 'Empty trash' });
    await user.click(buttons[buttons.length - 1]);

    return utils;
  };

  it('still refreshes when one library fails, since the others were emptied', async () => {
    emptyTrash.mockReset();
    emptyTrash
      .mockResolvedValueOnce(undefined as never)
      .mockRejectedValueOnce(new Error('locked'));

    const { onRefreshLibraries } = await renderTrash();

    await waitFor(() => expect(onRefreshLibraries).toHaveBeenCalled());
    expect(toast.error).toHaveBeenCalledWith(
      '1 of 2 libraries could not be emptied.',
      { title: 'Empty trash' }
    );
  });

  it('says nothing when every library is emptied', async () => {
    emptyTrash.mockReset();
    emptyTrash.mockResolvedValue(undefined as never);

    const { onRefreshLibraries } = await renderTrash();

    await waitFor(() => expect(onRefreshLibraries).toHaveBeenCalled());
    expect(toast.error).not.toHaveBeenCalled();
  });
});
