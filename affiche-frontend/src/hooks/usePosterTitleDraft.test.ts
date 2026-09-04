import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

import { usePosterTitleDraft } from './usePosterTitleDraft';
import { postersApi } from '../api';

vi.mock('../api', () => ({
  postersApi: { getTranslatedTitle: vi.fn() },
}));

const getTranslatedTitle = vi.mocked(postersApi.getTranslatedTitle);

const render = (overrides = {}) =>
  renderHook(() =>
    usePosterTitleDraft({
      defaultTitle: 'Arrival',
      mediaType: 'movie',
      tmdbId: 329865,
      ...overrides,
    })
  );

beforeEach(() => {
  getTranslatedTitle.mockReset();
  getTranslatedTitle.mockResolvedValue({ title: 'Premier Contact' });
});

describe('usePosterTitleDraft', () => {
  it('starts on the default title, with no language chosen', () => {
    const { result } = render();

    expect(result.current.title).toBe('Arrival');
    expect(result.current.language).toBe('');
  });

  it('replaces the title with the provider translation', async () => {
    const { result } = render();

    await act(async () => { await result.current.changeLanguage('fr'); });

    expect(result.current.title).toBe('Premier Contact');
    expect(result.current.language).toBe('fr');
  });

  it('asks about the season when the poster is for one', async () => {
    const { result } = render({ seasonNumber: 2 });

    await act(async () => { await result.current.changeLanguage('fr'); });

    expect(getTranslatedTitle).toHaveBeenCalledWith(
      expect.objectContaining({ language: 'fr', season_number: 2 })
    );
  });

  it('restores the default title for Original, without a request', async () => {
    const { result } = render();
    await act(async () => { await result.current.changeLanguage('fr'); });
    getTranslatedTitle.mockClear();

    await act(async () => { await result.current.changeLanguage(''); });

    expect(result.current.title).toBe('Arrival');
    expect(getTranslatedTitle).not.toHaveBeenCalled();
  });

  it('reports a lookup in flight, and stops when it lands', async () => {
    let resolve: (value: { title: string }) => void = () => {};
    getTranslatedTitle.mockReturnValueOnce(new Promise((r) => { resolve = r; }));

    const { result } = render();
    let pending: Promise<void> = Promise.resolve();
    act(() => { pending = result.current.changeLanguage('fr'); });
    await waitFor(() => expect(result.current.isTranslating).toBe(true));

    await act(async () => {
      resolve({ title: 'Premier Contact' });
      await pending;
    });

    expect(result.current.isTranslating).toBe(false);
  });

  it('keeps the current title when the provider has no localized one', async () => {
    getTranslatedTitle.mockResolvedValue({ title: '' });

    const { result } = render();
    await act(async () => { await result.current.changeLanguage('fr'); });

    expect(result.current.title).toBe('Arrival');
    expect(result.current.notFound).toBe(true);
  });

  it('treats a failed lookup as the same dead end as an empty one', async () => {
    getTranslatedTitle.mockRejectedValue(new Error('provider is down'));

    const { result } = render();
    await act(async () => { await result.current.changeLanguage('fr'); });

    expect(result.current.notFound).toBe(true);
    expect(result.current.title).toBe('Arrival');
    expect(result.current.isTranslating).toBe(false);
  });

  it('clears the not-found notice when the user types over the title', async () => {
    getTranslatedTitle.mockResolvedValue({ title: '' });
    const { result } = render();
    await act(async () => { await result.current.changeLanguage('fr'); });

    act(() => result.current.changeTitle('Arrival (2016)'));

    expect(result.current.notFound).toBe(false);
    expect(result.current.title).toBe('Arrival (2016)');
  });

  it('clears the not-found notice when another language is tried', async () => {
    getTranslatedTitle.mockResolvedValue({ title: '' });
    const { result } = render();
    await act(async () => { await result.current.changeLanguage('fr'); });

    getTranslatedTitle.mockResolvedValue({ title: 'La llegada' });
    await act(async () => { await result.current.changeLanguage('es'); });

    expect(result.current.notFound).toBe(false);
    expect(result.current.title).toBe('La llegada');
  });
});
