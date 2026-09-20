import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

import { useItemNeighbours } from './useItemNeighbours';
import { libraryApi } from '../api';
import type { Library, LibraryItem } from '../types';

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  libraryApi: { getLibraryItemIds: vi.fn(), getItem: vi.fn() },
}));

const FILMS = { id: 2, media_server_id: 1, name: 'Films', library_type: 'movie' } as Library;
const film = (id: number, title: string) => ({ id, library_id: 2, title }) as LibraryItem;
const [ALIEN, BRAZIL, HEAT, ZODIAC] = [film(1, 'Alien'), film(2, 'Brazil'), film(3, 'Heat'), film(4, 'Zodiac')];
const LISTING = { search: 'a', sort: { by: 'year', dir: 'desc' as const } };

const ids = vi.mocked(libraryApi.getLibraryItemIds);
const getItem = vi.mocked(libraryApi.getItem);

beforeEach(() => {
  ids.mockReset().mockResolvedValue([1, 2, 3, 4]);
  getItem.mockReset().mockImplementation(async (_s, _l, id) => [ALIEN, BRAZIL, HEAT, ZODIAC][id - 1]);
});

const run = (item: LibraryItem, items: LibraryItem[], hasMore: boolean, library: Library | null = FILMS) =>
  renderHook(() => useItemNeighbours({
    library: library ?? undefined, item, items, hasMore, listing: LISTING, enabled: true,
  }));

describe('useItemNeighbours', () => {
  it('answers from the loaded items when they hold both neighbours', () => {
    const { result } = run(BRAZIL, [ALIEN, BRAZIL, HEAT], true);

    expect(result.current).toEqual({ previous: ALIEN, next: HEAT });
    expect(ids).not.toHaveBeenCalled();
  });

  it('finds the next item beyond the last loaded one, in the listing order', async () => {
    const { result } = run(HEAT, [ALIEN, BRAZIL, HEAT], true);

    await waitFor(() => expect(result.current.next).toEqual(ZODIAC));
    expect(result.current.previous).toEqual(BRAZIL);
    expect(ids).toHaveBeenCalledWith(1, 2, expect.objectContaining({ search: 'a', sortBy: 'year', sortDir: 'desc' }));
  });

  it('gives a deep-linked item both neighbours', async () => {
    const { result } = run(HEAT, [], true);

    await waitFor(() => expect(result.current).toEqual({ previous: BRAZIL, next: ZODIAC }));
  });

  it('keeps to the loaded items in All libraries, which has no single listing to ask', () => {
    const { result } = run(HEAT, [ALIEN, BRAZIL, HEAT], true, null);

    expect(result.current).toEqual({ previous: BRAZIL, next: undefined });
    expect(ids).not.toHaveBeenCalled();
  });
});
