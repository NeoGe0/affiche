import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

import { resetAppVersionStore, useAppVersion } from './useAppVersion';
import { settingsApi } from '../api';
import type { AppSettingsInfo } from '../types';

vi.mock('../api', () => ({
  settingsApi: { getSettingsInfo: vi.fn() },
}));

const info = (version: string) =>
  ({ version, encryption_key_secure: true, database: 'sqlite' }) satisfies AppSettingsInfo;

const getSettingsInfo = vi.mocked(settingsApi.getSettingsInfo);

beforeEach(() => {
  resetAppVersionStore();
  getSettingsInfo.mockReset();
  getSettingsInfo.mockResolvedValue(info('0.1.0'));
});

describe('useAppVersion', () => {
  it('reports no version until the request resolves', async () => {
    const { result } = renderHook(() => useAppVersion());

    expect(result.current.version).toBeNull();
    await waitFor(() => expect(result.current.version).toBe('0.1.0'));
  });

  it('fetches once for several readers mounted together', async () => {
    const a = renderHook(() => useAppVersion());
    const b = renderHook(() => useAppVersion());

    await waitFor(() => expect(a.result.current.version).toBe('0.1.0'));
    expect(b.result.current.version).toBe('0.1.0');
    expect(getSettingsInfo).toHaveBeenCalledTimes(1);
  });

  it('serves a remount from the cache, without refetching', async () => {
    const first = renderHook(() => useAppVersion());
    await waitFor(() => expect(first.result.current.version).toBe('0.1.0'));
    first.unmount();

    const second = renderHook(() => useAppVersion());

    expect(second.result.current.version).toBe('0.1.0');
    expect(getSettingsInfo).toHaveBeenCalledTimes(1);
  });

  it('notifies a reader that mounted while the request was still in flight', async () => {
    let resolve: (value: AppSettingsInfo) => void = () => {};
    getSettingsInfo.mockReturnValueOnce(new Promise((r) => { resolve = r; }));

    const first = renderHook(() => useAppVersion());
    const second = renderHook(() => useAppVersion());
    expect(second.result.current.version).toBeNull();

    resolve(info('0.2.0'));

    await waitFor(() => expect(first.result.current.version).toBe('0.2.0'));
    expect(second.result.current.version).toBe('0.2.0');
  });

  it('stays silent on failure, and does not retry on the next mount', async () => {
    getSettingsInfo.mockRejectedValue(new Error('backend is down'));

    const first = renderHook(() => useAppVersion());
    await waitFor(() => expect(getSettingsInfo).toHaveBeenCalledTimes(1));
    expect(first.result.current.version).toBeNull();
    first.unmount();

    const second = renderHook(() => useAppVersion());

    expect(second.result.current.version).toBeNull();
    expect(getSettingsInfo).toHaveBeenCalledTimes(1);
  });

  it('treats a version without a suffix as a stable release', async () => {
    const { result } = renderHook(() => useAppVersion());

    await waitFor(() => expect(result.current.version).toBe('0.1.0'));
    expect(result.current.isPrerelease).toBe(false);
  });

  it('flags a semver pre-release', async () => {
    getSettingsInfo.mockResolvedValue(info('0.1.0-beta.1'));

    const { result } = renderHook(() => useAppVersion());

    await waitFor(() => expect(result.current.version).toBe('0.1.0-beta.1'));
    expect(result.current.isPrerelease).toBe(true);
  });

  it('does not call an unknown version a pre-release', () => {
    const { result } = renderHook(() => useAppVersion());

    expect(result.current.version).toBeNull();
    expect(result.current.isPrerelease).toBe(false);
  });
});
