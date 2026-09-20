import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

import { resetItemArtworkCache, useItemArtwork } from './useItemArtwork';
import { postersApi } from '../api';

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  postersApi: { getPosters: vi.fn() },
}));

const getPosters = vi.mocked(postersApi.getPosters);
const ALIEN = { mediaType: 'movie' as const, tmdbId: 348 };
const POSTER = { url: 'https://img/a.jpg', provider: 'tmdb', rank: 0, rank_score: 1 };

beforeEach(() => {
  resetItemArtworkCache();
  getPosters.mockReset();
});

describe('useItemArtwork', () => {
  it('asks nothing while held back', () => {
    renderHook(() => useItemArtwork(ALIEN, false));

    expect(getPosters).not.toHaveBeenCalled();
  });

  it('reuses a recent answer for the same title instead of asking the providers again', async () => {
    getPosters.mockResolvedValue([POSTER]);
    const first = renderHook(() => useItemArtwork(ALIEN, true));
    await waitFor(() => expect(first.result.current.posters).toEqual([POSTER]));
    first.unmount();

    const again = renderHook(() => useItemArtwork(ALIEN, true));

    expect(again.result.current.posters).toEqual([POSTER]);
    expect(getPosters).toHaveBeenCalledTimes(1);
  });

  it('tries again after a failure rather than remembering it', async () => {
    getPosters.mockRejectedValueOnce(new Error('TMDB is down')).mockResolvedValue([POSTER]);
    const first = renderHook(() => useItemArtwork(ALIEN, true));
    await waitFor(() => expect(first.result.current.error).toBe('TMDB is down'));
    first.unmount();

    const again = renderHook(() => useItemArtwork(ALIEN, true));

    await waitFor(() => expect(again.result.current.posters).toEqual([POSTER]));
    expect(getPosters).toHaveBeenCalledTimes(2);
  });
});
