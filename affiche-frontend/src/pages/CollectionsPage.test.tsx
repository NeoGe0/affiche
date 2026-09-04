import { describe, expect, it, vi, beforeEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';

import { CollectionsPage } from './CollectionsPage';
import { collectionsApi, libraryApi, postersApi } from '../api';
import type { Collection, Library } from '../types';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();
  return {
    ...actual,
    collectionsApi: {
      ...actual.collectionsApi,
      getCollections: vi.fn(),
      getCollection: vi.fn(),
      createCollection: vi.fn(),
      deleteCollection: vi.fn(),
      resolveIds: vi.fn().mockResolvedValue({ status: 'started', task_id: 't1', message: 'ok' }),
    },
    libraryApi: {
      ...actual.libraryApi,
      getLibrarySettings: vi.fn().mockResolvedValue({ upload_enabled: true }),
    },
    postersApi: {
      ...actual.postersApi,
      getPosters: vi.fn().mockResolvedValue([]),
      getCollectionPosters: vi.fn().mockResolvedValue([]),
      searchPosters: vi.fn().mockResolvedValue([]),
      uploadCustomPoster: vi.fn(),
      applyCollectionPoster: vi.fn().mockResolvedValue(undefined),
    },
  };
});

vi.mock('../components/image', () => ({
  PosterPreview: () => <div data-testid="preview" />,
  PosterStyleControls: () => null,
}));

const toast = { error: vi.fn(), success: vi.fn(), info: vi.fn(), show: vi.fn() };
vi.mock('../context/ToastContext', () => ({ useToast: () => toast }));

type StreamHandlers = NonNullable<Parameters<typeof import('../hooks').useEventStream>[0]>;
let handlers: StreamHandlers = {};

vi.mock('../hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../hooks')>()),
  useEventStream: (options: StreamHandlers) => {
    handlers = options;
  },
}));

const MOVIES: Library = { id: 2, media_server_id: 1, name: 'Movies', library_type: 'movie' };

const collection = (overrides: Partial<Collection> = {}): Collection => ({
  id: 10, library_id: 2, title: 'Alien Saga', member_count: 2, child_count: 2,
  processed: false, locked: false, tmdb_collection_id: null, ...overrides,
});

const getCollections = vi.mocked(collectionsApi.getCollections);

const renderPage = (props: Partial<Parameters<typeof CollectionsPage>[0]> = {}) =>
  render(
    <CollectionsPage
      mediaServerId={1}
      mediaServerName="Plex"
      libraries={[MOVIES]}
      selectedLibraryId={2}
      {...props}
    />
  );

beforeEach(() => {
  toast.error.mockReset();

  vi.mocked(collectionsApi.resolveIds).mockClear();
  vi.mocked(libraryApi.getLibrarySettings).mockResolvedValue(
    { upload_enabled: true } as Awaited<ReturnType<typeof libraryApi.getLibrarySettings>>);
  getCollections.mockClear();
  getCollections.mockResolvedValue({ collections: [collection()], total: 1, page: 0, page_size: 50 });
});

describe('CollectionsPage', () => {
  it('lists the library\'s collections', async () => {
    renderPage();

    expect(await screen.findByText('Alien Saga')).toBeInTheDocument();
  });

  it('asks for a library when none is selected', () => {

    renderPage({ selectedLibraryId: undefined });

    expect(screen.getByText('Pick a library')).toBeInTheDocument();
    expect(getCollections).not.toHaveBeenCalled();
  });

  it('points an empty library at the setting that fills it', async () => {

    getCollections.mockResolvedValue({ collections: [], total: 0, page: 0, page_size: 50 });

    renderPage();

    expect(await screen.findByText(/Track collections/)).toBeInTheDocument();
  });

  it('surfaces the media server\'s refusal instead of pretending the write worked', async () => {

    vi.mocked(collectionsApi.getCollection).mockResolvedValue({
      ...collection(), members: [],
    });
    vi.mocked(collectionsApi.deleteCollection).mockRejectedValue(
      new Error('The media server would not delete the collection.')
    );

    renderPage();
    fireEvent.click(await screen.findByText('Alien Saga'));
    fireEvent.click(await screen.findByRole('button', { name: /delete/i }));

    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: /^delete$/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(toast.error.mock.calls[0][0]).toMatch(/would not delete/i);
  });

  it('reports how many members the media server holds beyond what Affiche synced', async () => {
    getCollections.mockResolvedValue({
      collections: [collection({ member_count: 2, child_count: 7 })],
      total: 1, page: 0, page_size: 50,
    });

    renderPage();

    expect(await screen.findByText('2 items of 7')).toBeInTheDocument();
  });

  it('refetches when a sync writes this library\'s collection posters', async () => {

    getCollections.mockResolvedValue({
      collections: [collection()], total: 1, page: 0, page_size: 50,
    });
    renderPage();
    await screen.findByText('Alien Saga');
    const before = getCollections.mock.calls.length;

    await act(async () => { handlers.onLibrarySynced?.(1, MOVIES.id); });

    await waitFor(() => expect(getCollections.mock.calls.length).toBe(before + 1));
  });

  it('ignores a sync of a library it is not showing', async () => {
    getCollections.mockResolvedValue({
      collections: [collection()], total: 1, page: 0, page_size: 50,
    });
    renderPage();
    await screen.findByText('Alien Saga');
    const before = getCollections.mock.calls.length;

    await act(async () => { handlers.onLibrarySynced?.(1, 999); });

    expect(getCollections.mock.calls.length).toBe(before);
  });
  it('picks a poster for a collection by hand', async () => {

    getCollections.mockResolvedValue({
      collections: [collection()], total: 1, page: 0, page_size: 50,
    });
    vi.mocked(collectionsApi.getCollection).mockResolvedValue({ ...collection(), members: [] });
    renderPage();

    fireEvent.click(await screen.findByText('Alien Saga'));
    fireEvent.click(await screen.findByRole('button', { name: /select poster/i }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('heading', { name: /Alien Saga/ })).toBeInTheDocument();
  });

  it('defaults the upload toggle to the library setting', async () => {

    getCollections.mockResolvedValue({
      collections: [collection()], total: 1, page: 0, page_size: 50,
    });
    vi.mocked(collectionsApi.getCollection).mockResolvedValue({ ...collection(), members: [] });
    renderPage();

    fireEvent.click(await screen.findByText('Alien Saga'));
    fireEvent.click(await screen.findByRole('button', { name: /select poster/i }));
    await screen.findByRole('dialog');

    expect(await screen.findByLabelText(/upload to library/i)).toBeChecked();
  });

  it('leaves the upload toggle off for a library that does not upload', async () => {
    getCollections.mockResolvedValue({
      collections: [collection()], total: 1, page: 0, page_size: 50,
    });
    vi.mocked(collectionsApi.getCollection).mockResolvedValue({ ...collection(), members: [] });
    vi.mocked(libraryApi.getLibrarySettings).mockResolvedValue(
      { upload_enabled: false } as Awaited<ReturnType<typeof libraryApi.getLibrarySettings>>);
    renderPage();

    fireEvent.click(await screen.findByText('Alien Saga'));
    fireEvent.click(await screen.findByRole('button', { name: /select poster/i }));
    await screen.findByRole('dialog');

    expect(await screen.findByLabelText(/upload to library/i)).not.toBeChecked();
  });

  it('does not browse providers for a collection no catalogue matched', async () => {

    getCollections.mockResolvedValue({
      collections: [collection()], total: 1, page: 0, page_size: 50,
    });
    vi.mocked(collectionsApi.getCollection).mockResolvedValue({ ...collection(), members: [] });
    renderPage();

    fireEvent.click(await screen.findByText('Alien Saga'));
    fireEvent.click(await screen.findByRole('button', { name: /select poster/i }));
    await screen.findByRole('dialog');

    expect(postersApi.getPosters).not.toHaveBeenCalled();
    expect(postersApi.getCollectionPosters).not.toHaveBeenCalled();
  });

  it('browses the catalogue for a collection that matched one', async () => {

    const matched = collection({ tmdb_collection_id: 8091 });
    getCollections.mockResolvedValue({
      collections: [matched], total: 1, page: 0, page_size: 50,
    });
    vi.mocked(collectionsApi.getCollection).mockResolvedValue({ ...matched, members: [] });
    renderPage();

    fireEvent.click(await screen.findByText('Alien Saga'));
    fireEvent.click(await screen.findByRole('button', { name: /select poster/i }));
    await screen.findByRole('dialog');

    await waitFor(() => expect(postersApi.getCollectionPosters).toHaveBeenCalled());
    expect(vi.mocked(postersApi.getCollectionPosters).mock.calls[0][0])
      .toMatchObject({ collectionId: 8091 });

    expect(postersApi.getPosters).not.toHaveBeenCalled();
  });
});

describe('CollectionsPage — matching against the catalogue', () => {

  const chooseFromMenu = (label: RegExp) => {
    fireEvent.click(screen.getByTitle('More actions'));
    fireEvent.click(screen.getByRole('menuitem', { name: label }));
  };

  const listOneCollection = () => {
    getCollections.mockResolvedValue({
      collections: [collection()], total: 1, page: 0, page_size: 50,
    });
  };

  it('confirms before starting, the way the library actions do', async () => {
    listOneCollection();
    renderPage();
    await screen.findByText('Alien Saga');

    fireEvent.click(screen.getByRole('button', { name: /match collections/i }));

    expect(await screen.findByRole('heading', { name: /match collections/i })).toBeInTheDocument();
    expect(collectionsApi.resolveIds).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Match' }));

    await waitFor(() =>
      expect(collectionsApi.resolveIds).toHaveBeenCalledWith(1, MOVIES.id));
  });

  it('starts nothing when the confirmation is dismissed', async () => {
    listOneCollection();
    renderPage();
    await screen.findByText('Alien Saga');

    fireEvent.click(screen.getByRole('button', { name: /match collections/i }));
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel' }));

    expect(collectionsApi.resolveIds).not.toHaveBeenCalled();
  });

  it('leaves Refresh as a plain re-listing', async () => {
    listOneCollection();
    renderPage();
    await screen.findByText('Alien Saga');
    vi.mocked(collectionsApi.resolveIds).mockClear();
    const before = getCollections.mock.calls.length;

    chooseFromMenu(/refresh/i);

    expect(collectionsApi.resolveIds).not.toHaveBeenCalled();
    await waitFor(() => expect(getCollections.mock.calls.length).toBe(before + 1));
  });

  it('reports a refused start rather than pretending it ran', async () => {
    listOneCollection();
    vi.mocked(collectionsApi.resolveIds).mockRejectedValueOnce(new Error('busy'));
    renderPage();
    await screen.findByText('Alien Saga');

    fireEvent.click(screen.getByRole('button', { name: /match collections/i }));
    fireEvent.click(await screen.findByRole('button', { name: 'Match' }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });
});
