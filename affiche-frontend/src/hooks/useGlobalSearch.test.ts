import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useGlobalSearch } from './useGlobalSearch';
import { searchApi } from '../api';
import type { SearchHit, SearchResults } from '../types';

vi.mock('../api', async () => ({
  searchApi: { searchItems: vi.fn() },

  errorMessage: (await vi.importActual<typeof import('../api/client')>('../api/client')).errorMessage,
}));

const hit = (title: string) => ({ id: 1, library_id: 1, title }) as SearchHit;

const results = (...titles: string[]) =>
  ({
    items: titles.map(hit),
    total: titles.length,
    total_pages: 1,
    page: 0,
    page_size: 25,
  }) satisfies SearchResults;

const searchItems = vi.mocked(searchApi.searchItems);

beforeEach(() => {
  vi.useFakeTimers();
  searchItems.mockReset();
  searchItems.mockResolvedValue(results('Alien'));
});

afterEach(() => {
  vi.useRealTimers();
});

const settle = async () => {
  await act(async () => {
    await vi.runAllTimersAsync();
  });
};

describe('useGlobalSearch', () => {
  it('does not search a term below the floor', async () => {
    const { result } = renderHook(() => useGlobalSearch('a'));

    await settle();

    expect(searchItems).not.toHaveBeenCalled();
    expect(result.current.isActive).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it('reports loading from the keystroke, before the debounce has even elapsed', () => {
    const { result } = renderHook(() => useGlobalSearch('alien'));

    expect(result.current.isLoading).toBe(true);
    expect(searchItems).not.toHaveBeenCalled();
  });

  it('searches once the debounce elapses, and publishes the hits', async () => {
    const { result } = renderHook(() => useGlobalSearch('alien'));

    await settle();

    expect(searchItems).toHaveBeenCalledExactlyOnceWith('alien', 25);
    expect(result.current.hits.map((h) => h.title)).toEqual(['Alien']);
    expect(result.current.isLoading).toBe(false);
  });

  it('fires one request for a term typed a character at a time', async () => {
    const { rerender } = renderHook(({ term }) => useGlobalSearch(term), {
      initialProps: { term: 'al' },
    });

    rerender({ term: 'ali' });
    rerender({ term: 'alie' });
    rerender({ term: 'alien' });
    await settle();

    expect(searchItems).toHaveBeenCalledExactlyOnceWith('alien', 25);
  });

  it('searches the trimmed term', async () => {
    renderHook(() => useGlobalSearch('  alien  '));

    await settle();

    expect(searchItems).toHaveBeenCalledExactlyOnceWith('alien', 25);
  });

  it('shows nothing while a new term is pending, rather than the previous answer', async () => {
    const { result, rerender } = renderHook(({ term }) => useGlobalSearch(term), {
      initialProps: { term: 'alien' },
    });
    await settle();
    expect(result.current.hits).toHaveLength(1);

    rerender({ term: 'dune' });

    expect(result.current.hits).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });

  it('never publishes a response to a term the user has moved on from', async () => {

    let resolveStale: (value: SearchResults) => void = () => {};
    searchItems.mockReturnValueOnce(new Promise((resolve) => { resolveStale = resolve; }));

    const { result, rerender } = renderHook(({ term }) => useGlobalSearch(term), {
      initialProps: { term: 'alien' },
    });
    await act(async () => { await vi.advanceTimersByTimeAsync(300); });

    searchItems.mockResolvedValue(results('Dune'));
    rerender({ term: 'dune' });
    await settle();
    expect(result.current.hits.map((h) => h.title)).toEqual(['Dune']);

    await act(async () => { resolveStale(results('Alien')); });

    expect(result.current.hits.map((h) => h.title)).toEqual(['Dune']);
  });

  it('drops back to inactive when the term is cleared', async () => {
    const { result, rerender } = renderHook(({ term }) => useGlobalSearch(term), {
      initialProps: { term: 'alien' },
    });
    await settle();

    rerender({ term: '' });

    expect(result.current.isActive).toBe(false);
    expect(result.current.hits).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });

  it('reports a failure in place of the hits', async () => {
    searchItems.mockRejectedValue(new Error('500'));

    const { result } = renderHook(() => useGlobalSearch('alien'));
    await settle();

    expect(result.current.error).toBe('500');
    expect(result.current.hits).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });

  it('flags a result set the server had to cut short', async () => {
    searchItems.mockResolvedValue({ ...results('Alien'), total: 400 });

    const { result } = renderHook(() => useGlobalSearch('alien'));
    await settle();

    expect(result.current.isTruncated).toBe(true);
    expect(result.current.total).toBe(400);
  });

  it('does not call a complete result set truncated', async () => {
    const { result } = renderHook(() => useGlobalSearch('alien'));
    await settle();

    expect(result.current.isTruncated).toBe(false);
  });
});
