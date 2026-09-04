import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

import { useLibraryItems } from './useLibraryItems';
import { libraryApi } from '../api';
import type { Library, LibraryItem, PaginatedLibraryItems } from '../types';

vi.mock('../api', () => ({
  libraryApi: { getLibraryItems: vi.fn(), getTrashItems: vi.fn() },
  errorMessage: (_error: unknown, fallback: string) => fallback,
}));

vi.mock('../context/ToastContext', () => ({
  useToast: () => ({ error: vi.fn(), success: vi.fn(), info: vi.fn(), show: vi.fn() }),
}));

const films = { id: 1, media_server_id: 7, name: 'Films' } as Library;
const shows = { id: 2, media_server_id: 7, name: 'TV Shows' } as Library;

const page = (libraryId: number, ...titles: string[]) =>
  ({
    items: titles.map((title, index) => (
      { id: libraryId * 100 + index, library_id: libraryId, title } as LibraryItem
    )),
    total: 500,
    total_pages: 10,
    page: 0,
    page_size: 50,
  }) satisfies PaginatedLibraryItems;

const getTrashItems = vi.mocked(libraryApi.getTrashItems);

const libraries = [films, shows];
const sort = { by: 'title', dir: 'asc' as const };

const options = (selectedLibrary: Library) => ({
  mediaServerId: 7,
  libraries,
  selectedLibrary,
  isTrash: true,
  search: '',
  filter: 'all' as const,
  sort,
});

beforeEach(() => {
  getTrashItems.mockReset();
});

describe('useLibraryItems', () => {
  it('drops a load-more that lands after the user switched library', async () => {
    getTrashItems.mockResolvedValue(page(2, 'Firefly'));
    const { result, rerender } = renderHook(
      ({ library }: { library: Library }) => useLibraryItems(options(library)),
      { initialProps: { library: shows } }
    );
    await waitFor(() => expect(result.current.items).toHaveLength(1));

    let releaseShows: (value: PaginatedLibraryItems) => void = () => {};
    getTrashItems.mockReturnValueOnce(new Promise((resolve) => { releaseShows = resolve; }));
    act(() => { result.current.handleLoadMore(); });

    getTrashItems.mockResolvedValue(page(1, 'Alien'));
    rerender({ library: films });
    await waitFor(() => expect(result.current.items.map((i) => i.title)).toEqual(['Alien']));

    await act(async () => { releaseShows(page(2, 'Serenity')); });

    expect(result.current.items.map((i) => i.title)).toEqual(['Alien']);
    expect(result.current.items.every((i) => i.library_id === films.id)).toBe(true);
  });

  it('refreshes every page the list has already loaded, not just the first', async () => {

    getTrashItems.mockResolvedValue(page(2, 'Firefly'));
    const { result } = renderHook(() => useLibraryItems(options(shows)));
    await waitFor(() => expect(result.current.items).toHaveLength(1));

    getTrashItems.mockResolvedValue(page(2, 'Serenity'));
    await act(async () => { result.current.handleLoadMore(); });
    expect(result.current.items).toHaveLength(2);

    await act(async () => { await result.current.fetchItems(); });

    expect(getTrashItems).toHaveBeenLastCalledWith(7, shows.id,
      expect.objectContaining({ page: 0, pageSize: 100 }));
  });

  it('asks for one page again when nothing has been loaded yet', async () => {
    getTrashItems.mockResolvedValue(page(2, 'Firefly'));
    const { result } = renderHook(() => useLibraryItems(options(shows)));
    await waitFor(() => expect(result.current.items).toHaveLength(1));

    expect(getTrashItems).toHaveBeenLastCalledWith(7, shows.id,
      expect.objectContaining({ page: 0, pageSize: 50 }));
  });

  it('drops a first page that lands after the user switched library', async () => {
    let releaseShows: (value: PaginatedLibraryItems) => void = () => {};
    getTrashItems.mockReturnValueOnce(new Promise((resolve) => { releaseShows = resolve; }));

    const { result, rerender } = renderHook(
      ({ library }: { library: Library }) => useLibraryItems(options(library)),
      { initialProps: { library: shows } }
    );

    getTrashItems.mockResolvedValue(page(1, 'Alien'));
    rerender({ library: films });
    await waitFor(() => expect(result.current.items.map((i) => i.title)).toEqual(['Alien']));

    await act(async () => { releaseShows(page(2, 'Firefly')); });

    expect(result.current.items.map((i) => i.title)).toEqual(['Alien']);
  });
});
