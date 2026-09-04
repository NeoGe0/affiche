import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

import {
  invalidatePosterConfig,
  resetPosterConfigStore,
  usePosterConfig,
} from './usePosterConfig';
import { settingsApi } from '../api';
import type { PosterConfig } from '../types';

vi.mock('../api', () => ({
  settingsApi: { getPosterConfig: vi.fn() },
}));

const config = (jpegQuality: number) =>
  ({
    overlay_options: {},
    text_options: {},
    generation_options: { jpeg_quality: jpegQuality },
  }) as unknown as PosterConfig;

const getPosterConfig = vi.mocked(settingsApi.getPosterConfig);

beforeEach(() => {
  resetPosterConfigStore();
  getPosterConfig.mockReset();
  getPosterConfig.mockResolvedValue(config(90));
});

describe('usePosterConfig', () => {
  it('reports loading until the config arrives', async () => {
    const { result } = renderHook(() => usePosterConfig());

    expect(result.current).toMatchObject({ config: null, isLoading: true });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.config).toEqual(config(90));
  });

  it('serves a remount from the cache, without refetching', async () => {
    const first = renderHook(() => usePosterConfig());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    first.unmount();

    const second = renderHook(() => usePosterConfig());

    expect(second.result.current.config).toEqual(config(90));
    expect(second.result.current.isLoading).toBe(false);
    expect(getPosterConfig).toHaveBeenCalledTimes(1);
  });

  it('fetches once for several readers mounted together', async () => {
    const a = renderHook(() => usePosterConfig());
    const b = renderHook(() => usePosterConfig());

    await waitFor(() => expect(a.result.current.isLoading).toBe(false));
    expect(b.result.current.config).toEqual(config(90));
    expect(getPosterConfig).toHaveBeenCalledTimes(1);
  });

  it('refetches after a write, and every mounted reader sees the new values', async () => {
    const { result } = renderHook(() => usePosterConfig());
    await waitFor(() => expect(result.current.config).toEqual(config(90)));

    getPosterConfig.mockResolvedValue(config(75));
    act(() => invalidatePosterConfig());

    await waitFor(() => expect(result.current.config).toEqual(config(75)));
    expect(getPosterConfig).toHaveBeenCalledTimes(2);
  });

  it('defers the refetch to the next reader when nothing is mounted', async () => {
    const first = renderHook(() => usePosterConfig());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    first.unmount();

    invalidatePosterConfig();
    expect(getPosterConfig).toHaveBeenCalledTimes(1);

    getPosterConfig.mockResolvedValue(config(75));
    const second = renderHook(() => usePosterConfig());

    await waitFor(() => expect(second.result.current.config).toEqual(config(75)));
    expect(getPosterConfig).toHaveBeenCalledTimes(2);
  });

  it('surfaces a failure instead of staying stuck on loading', async () => {
    getPosterConfig.mockRejectedValue(new Error('500'));

    const { result } = renderHook(() => usePosterConfig());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error?.message).toBe('500');
    expect(result.current.config).toBeNull();
  });

  it('ignores a request that was in flight when the cache was invalidated', async () => {

    let resolveStale: (config: PosterConfig) => void = () => {};
    getPosterConfig.mockReturnValueOnce(new Promise((resolve) => { resolveStale = resolve; }));

    const { result } = renderHook(() => usePosterConfig());
    expect(result.current.isLoading).toBe(true);

    getPosterConfig.mockResolvedValue(config(75));
    act(() => invalidatePosterConfig());
    await waitFor(() => expect(result.current.config).toEqual(config(75)));

    await act(async () => {
      resolveStale(config(90));
    });

    expect(result.current.config).toEqual(config(75));
  });

  it('retries after a failure rather than caching it', async () => {
    getPosterConfig.mockRejectedValue(new Error('500'));
    const first = renderHook(() => usePosterConfig());
    await waitFor(() => expect(first.result.current.error).not.toBeNull());
    first.unmount();

    getPosterConfig.mockResolvedValue(config(90));
    const second = renderHook(() => usePosterConfig());

    await waitFor(() => expect(second.result.current.config).toEqual(config(90)));
  });
});
