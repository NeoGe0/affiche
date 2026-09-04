import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

import { reloadFonts, resetFontsStore, useFonts } from './useFonts';
import { fontsApi } from '../api';

vi.mock('../api', () => ({
  fontsApi: { getFonts: vi.fn() },
}));

const getFonts = vi.mocked(fontsApi.getFonts);

const injectedCss = () =>
  Array.from(document.head.querySelectorAll('style[data-affiche-fonts]'))
    .map((element) => element.textContent ?? '')
    .join('\n');

beforeEach(() => {
  resetFontsStore();
  getFonts.mockReset();
  getFonts.mockResolvedValue(['Inter.ttf', 'Roboto.otf']);
});

describe('useFonts', () => {
  it('reports loading until the list arrives', async () => {
    const { result } = renderHook(() => useFonts());

    expect(result.current).toMatchObject({ fonts: [], isLoading: true });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.fonts).toEqual(['Inter.ttf', 'Roboto.otf']);
  });

  it('fetches once for several readers mounted together', async () => {
    const a = renderHook(() => useFonts());
    const b = renderHook(() => useFonts());

    await waitFor(() => expect(a.result.current.isLoading).toBe(false));
    expect(b.result.current.fonts).toEqual(['Inter.ttf', 'Roboto.otf']);
    expect(getFonts).toHaveBeenCalledTimes(1);
  });

  it('serves a remount from the cache, without refetching', async () => {
    const first = renderHook(() => useFonts());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    first.unmount();

    const second = renderHook(() => useFonts());

    expect(second.result.current.fonts).toEqual(['Inter.ttf', 'Roboto.otf']);
    expect(second.result.current.isLoading).toBe(false);
    expect(getFonts).toHaveBeenCalledTimes(1);
  });

  it('registers an @font-face rule per file, named after the file without its extension', async () => {
    const { result } = renderHook(() => useFonts());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const css = injectedCss();
    expect(css).toContain('font-family: "Inter"');
    expect(css).toContain('font-family: "Roboto"');
    expect(css).toContain('Inter.ttf');
  });

  it('percent-encodes a file name in the @font-face url', async () => {
    getFonts.mockResolvedValue(['My Font.ttf']);

    const { result } = renderHook(() => useFonts());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(injectedCss()).toContain('My%20Font.ttf');
  });

  it('does not re-register a face the document already carries', async () => {
    const { result } = renderHook(() => useFonts());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    getFonts.mockResolvedValue(['Inter.ttf', 'Roboto.otf', 'Lato.ttf']);
    await act(async () => { await reloadFonts(); });

    const css = injectedCss();
    expect(css.match(/font-family: "Inter"/g)).toHaveLength(1);
    expect(css).toContain('font-family: "Lato"');
  });

  it('publishes a reload to every mounted reader', async () => {
    const a = renderHook(() => useFonts());
    const b = renderHook(() => useFonts());
    await waitFor(() => expect(a.result.current.isLoading).toBe(false));

    getFonts.mockResolvedValue(['Inter.ttf']);
    await act(async () => { await reloadFonts(); });

    expect(a.result.current.fonts).toEqual(['Inter.ttf']);
    expect(b.result.current.fonts).toEqual(['Inter.ttf']);
  });

  it('returns the new list from reload, for the caller that has to act on it', async () => {
    const { result } = renderHook(() => useFonts());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    getFonts.mockResolvedValue(['Lato.ttf']);
    let returned: string[] = [];
    await act(async () => { returned = await reloadFonts(); });

    expect(returned).toEqual(['Lato.ttf']);
  });

  it('rejects a failed reload rather than swallowing it, and keeps the current list', async () => {
    const { result } = renderHook(() => useFonts());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    getFonts.mockRejectedValue(new Error('upload failed'));
    await expect(reloadFonts()).rejects.toThrow('upload failed');
    expect(result.current.fonts).toEqual(['Inter.ttf', 'Roboto.otf']);
  });

  it('ignores a request that was in flight when the list was reloaded', async () => {

    let resolveStale: (fonts: string[]) => void = () => {};
    getFonts.mockReturnValueOnce(new Promise((resolve) => { resolveStale = resolve; }));

    const { result } = renderHook(() => useFonts());
    expect(result.current.isLoading).toBe(true);

    getFonts.mockResolvedValue(['Lato.ttf']);
    await act(async () => { await reloadFonts(); });
    expect(result.current.fonts).toEqual(['Lato.ttf']);

    await act(async () => { resolveStale(['Inter.ttf', 'Roboto.otf']); });

    expect(result.current.fonts).toEqual(['Lato.ttf']);
  });

  it('leaves the list unknown on failure, so the next mount retries', async () => {
    getFonts.mockRejectedValue(new Error('500'));
    const first = renderHook(() => useFonts());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    expect(first.result.current.fonts).toEqual([]);
    first.unmount();

    getFonts.mockResolvedValue(['Inter.ttf']);
    const second = renderHook(() => useFonts());

    await waitFor(() => expect(second.result.current.fonts).toEqual(['Inter.ttf']));
    expect(getFonts).toHaveBeenCalledTimes(2);
  });

  it('treats an empty list as a settled answer, not a missing one', async () => {
    getFonts.mockResolvedValue([]);
    const first = renderHook(() => useFonts());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    first.unmount();

    const second = renderHook(() => useFonts());

    expect(second.result.current.isLoading).toBe(false);
    expect(getFonts).toHaveBeenCalledTimes(1);
  });
});
