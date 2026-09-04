import { describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { usePosterBrowseQuery } from './usePosterBrowseQuery';

const render = (onSourceChanged = vi.fn(), overrides = {}) => ({
  onSourceChanged,
  ...renderHook(() =>
    usePosterBrowseQuery({
      itemTitle: 'Arrival',
      year: 2016,
      onSourceChanged,
      ...overrides,
    })
  ),
});

describe('usePosterBrowseQuery', () => {
  it('seeds the search box from the item', () => {
    const { result } = render();

    expect(result.current.searchTitle).toBe('Arrival');
    expect(result.current.searchYear).toBe('2016');
  });

  it('leaves the year box empty for an item with no year', () => {
    const { result } = render(vi.fn(), { year: undefined });

    expect(result.current.searchYear).toBe('');
    expect(result.current.yearFilter).toBeUndefined();
  });

  it('parses the year box into a filter', () => {
    const { result } = render();

    expect(result.current.yearFilter).toBe(2016);
  });

  it('treats a cleared year box as no filter rather than as zero', () => {
    const { result } = render();

    act(() => result.current.setSearchYear(''));

    expect(result.current.yearFilter).toBeUndefined();
  });

  it('drops the selection when the provider changes', () => {
    const { result, onSourceChanged } = render();

    act(() => result.current.changeProvider('tmdb'));

    expect(result.current.provider).toBe('tmdb');
    expect(onSourceChanged).toHaveBeenCalledTimes(1);
  });

  it('drops the selection when another season is browsed', () => {
    const { result, onSourceChanged } = render(vi.fn(), { seasonNumber: 1 });

    act(() => result.current.changeSearchSeasonNumber(3));

    expect(result.current.searchSeasonNumber).toBe(3);
    expect(onSourceChanged).toHaveBeenCalledTimes(1);
  });

  it('drops the selection when switching to the show artwork', () => {
    const { result, onSourceChanged } = render(vi.fn(), { seasonNumber: 1 });

    act(() => result.current.changeUseShowArt(true));

    expect(result.current.useShowArt).toBe(true);
    expect(onSourceChanged).toHaveBeenCalledTimes(1);
  });

  it('keeps the selection when only the language changes', () => {
    const { result, onSourceChanged } = render();

    act(() => result.current.changeLanguage('fr'));

    expect(result.current.language).toBe('fr');
    expect(onSourceChanged).not.toHaveBeenCalled();
  });

  it('keeps the selection while the search box is being typed in', () => {

    const { result, onSourceChanged } = render();

    act(() => result.current.setSearchTitle('Arriv'));

    expect(onSourceChanged).not.toHaveBeenCalled();
  });

  it('starts a season browse on the season that was opened', () => {
    const { result } = render(vi.fn(), { seasonNumber: 4 });

    expect(result.current.searchSeasonNumber).toBe(4);
    expect(result.current.useShowArt).toBe(false);
  });
});
