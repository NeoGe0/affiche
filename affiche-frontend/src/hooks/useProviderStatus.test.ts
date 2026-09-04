import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

import {
  reloadProviderStatus,
  resetProviderStatusStore,
  useProviderStatus,
} from './useProviderStatus';
import { configApi } from '../api';
import type { ServiceConfiguration } from '../types';

vi.mock('../api', () => ({
  configApi: { findConfigs: vi.fn() },
}));

const row = (
  name: string,
  overrides: Partial<ServiceConfiguration> = {},
): ServiceConfiguration => ({
  name,
  type: 'PROVIDER',
  url: 'https://api.example.com',
  enabled: true,
  configured: true,
  token_hint: null,
  ...overrides,
});

const findConfigs = vi.mocked(configApi.findConfigs);

beforeEach(() => {
  resetProviderStatusStore();
  findConfigs.mockReset();
  findConfigs.mockResolvedValue([row('tmdb')]);
});

describe('useProviderStatus', () => {
  it('reports loading until the configs arrive', async () => {
    const { result } = renderHook(() => useProviderStatus());

    expect(result.current).toMatchObject({
      configuredProviders: [],
      isAnyProviderConfigured: false,
      isLoading: true,
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.configuredProviders).toEqual(['tmdb']);
    expect(result.current.isAnyProviderConfigured).toBe(true);
  });

  it('fetches once for several readers mounted together', async () => {
    const a = renderHook(() => useProviderStatus());
    const b = renderHook(() => useProviderStatus());

    await waitFor(() => expect(a.result.current.isLoading).toBe(false));
    expect(b.result.current.configuredProviders).toEqual(['tmdb']);
    expect(findConfigs).toHaveBeenCalledTimes(1);
  });

  it('serves a remount from the cache, without refetching', async () => {
    const first = renderHook(() => useProviderStatus());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    first.unmount();

    const second = renderHook(() => useProviderStatus());

    expect(second.result.current.configuredProviders).toEqual(['tmdb']);
    expect(second.result.current.isLoading).toBe(false);
    expect(findConfigs).toHaveBeenCalledTimes(1);
  });

  it('lists a disabled provider as added but not as usable', async () => {
    findConfigs.mockResolvedValue([row('tmdb', { enabled: false })]);

    const { result } = renderHook(() => useProviderStatus());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.addedProviders).toEqual(['tmdb']);
    expect(result.current.configuredProviders).toEqual([]);
    expect(result.current.isAnyProviderConfigured).toBe(false);
  });

  it('excludes a provider whose key is still missing', async () => {
    findConfigs.mockResolvedValue([row('tmdb', { configured: false })]);

    const { result } = renderHook(() => useProviderStatus());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.configuredProviders).toEqual([]);
  });

  it('counts an open-API provider as usable without a key', async () => {

    findConfigs.mockResolvedValue([row('tvmaze', { configured: false })]);

    const { result } = renderHook(() => useProviderStatus());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.configuredProviders).toEqual(['tvmaze']);
  });

  it('excludes a self-hosted provider with no base URL', async () => {
    findConfigs.mockResolvedValue([row('shoko', { url: '' })]);

    const { result } = renderHook(() => useProviderStatus());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.addedProviders).toEqual(['shoko']);
    expect(result.current.configuredProviders).toEqual([]);
  });

  it('counts a provider that takes no base URL as usable without one', async () => {

    findConfigs.mockResolvedValue([row('tvdb', { url: '' })]);

    const { result } = renderHook(() => useProviderStatus());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.configuredProviders).toEqual(['tvdb']);
  });

  it('orders providers by the canonical listing order, not the API response order', async () => {
    findConfigs.mockResolvedValue([row('mediux'), row('tmdb'), row('fanart')]);

    const { result } = renderHook(() => useProviderStatus());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.addedProviders).toEqual(['tmdb', 'fanart', 'mediux']);
    expect(result.current.configuredProviders).toEqual(['tmdb', 'fanart', 'mediux']);
  });

  it('ignores a config row for a provider the frontend does not know', async () => {
    findConfigs.mockResolvedValue([row('tmdb'), row('not-a-provider')]);

    const { result } = renderHook(() => useProviderStatus());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.addedProviders).toEqual(['tmdb']);
  });

  it('keeps the previous list on screen while a reload runs', async () => {
    const { result } = renderHook(() => useProviderStatus());
    await waitFor(() => expect(result.current.configuredProviders).toEqual(['tmdb']));

    let resolve: (rows: ServiceConfiguration[]) => void = () => {};
    findConfigs.mockReturnValueOnce(new Promise((r) => { resolve = r; }));
    let reloaded: Promise<void> = Promise.resolve();
    act(() => { reloaded = reloadProviderStatus(); });

    expect(result.current.configuredProviders).toEqual(['tmdb']);
    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      resolve([row('tmdb'), row('fanart')]);
      await reloaded;
    });
    expect(result.current.configuredProviders).toEqual(['tmdb', 'fanart']);
  });

  it('publishes a reload to every mounted reader', async () => {
    const a = renderHook(() => useProviderStatus());
    const b = renderHook(() => useProviderStatus());
    await waitFor(() => expect(a.result.current.isLoading).toBe(false));

    findConfigs.mockResolvedValue([row('fanart')]);
    await act(async () => { await reloadProviderStatus(); });

    expect(a.result.current.configuredProviders).toEqual(['fanart']);
    expect(b.result.current.configuredProviders).toEqual(['fanart']);
  });

  it('ignores a request that was in flight when the status was reloaded', async () => {
    let resolveStale: (rows: ServiceConfiguration[]) => void = () => {};
    findConfigs.mockReturnValueOnce(new Promise((resolve) => { resolveStale = resolve; }));

    const { result } = renderHook(() => useProviderStatus());
    expect(result.current.isLoading).toBe(true);

    findConfigs.mockResolvedValue([row('fanart')]);
    await act(async () => { await reloadProviderStatus(); });
    expect(result.current.configuredProviders).toEqual(['fanart']);

    await act(async () => { resolveStale([row('tmdb')]); });

    expect(result.current.configuredProviders).toEqual(['fanart']);
  });

  it('closes the gate on failure, and retries on the next mount', async () => {
    findConfigs.mockRejectedValue(new Error('500'));
    const first = renderHook(() => useProviderStatus());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    expect(first.result.current.isAnyProviderConfigured).toBe(false);
    first.unmount();

    findConfigs.mockResolvedValue([row('tmdb')]);
    const second = renderHook(() => useProviderStatus());

    await waitFor(() => expect(second.result.current.configuredProviders).toEqual(['tmdb']));
    expect(findConfigs).toHaveBeenCalledTimes(2);
  });

  it('treats "no providers added" as a settled answer, not a missing one', async () => {
    findConfigs.mockResolvedValue([]);
    const first = renderHook(() => useProviderStatus());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    first.unmount();

    const second = renderHook(() => useProviderStatus());

    expect(second.result.current.isLoading).toBe(false);
    expect(findConfigs).toHaveBeenCalledTimes(1);
  });
});
