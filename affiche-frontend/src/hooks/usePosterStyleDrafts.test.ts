import { describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { usePosterStyleDrafts } from './usePosterStyleDrafts';
import type { PosterConfig } from '../types';

const config = (overrides: Record<string, unknown> = {}) =>
  ({
    overlay_options: { border_enabled: true, blur_amount: 50 },
    text_options: { font_name: 'Serif.ttf', all_caps: false },
    generation_options: { jpeg_quality: 85 },
    ...overrides,
  }) as unknown as PosterConfig;

describe('usePosterStyleDrafts', () => {
  it('serves the global config while nothing has been edited', () => {
    const { result } = renderHook(() => usePosterStyleDrafts(config()));

    expect(result.current.overlayOptions).toEqual({ border_enabled: true, blur_amount: 50 });
    expect(result.current.quality).toBe(85);
  });

  it('has nothing to offer until the config arrives', () => {

    const { result } = renderHook(() => usePosterStyleDrafts(null));

    expect(result.current.overlayOptions).toBeUndefined();
    expect(result.current.textOptions).toBeUndefined();
  });

  it('falls back to a usable quality before the config lands', () => {
    const { result } = renderHook(() => usePosterStyleDrafts(null));

    expect(result.current.quality).toBe(90);
  });

  it('picks up a config that arrives after mount, rather than freezing the first value', () => {

    const { result, rerender } = renderHook(({ c }) => usePosterStyleDrafts(c), {
      initialProps: { c: null as PosterConfig | null },
    });

    rerender({ c: config() });

    expect(result.current.overlayOptions).toEqual({ border_enabled: true, blur_amount: 50 });
  });

  it('merges an edit onto the config values it did not touch', () => {
    const { result } = renderHook(() => usePosterStyleDrafts(config()));

    act(() => result.current.changeOverlay({ blur_amount: 20 }));

    expect(result.current.overlayOptions).toEqual({ border_enabled: true, blur_amount: 20 });
  });

  it('merges a second edit onto the first', () => {
    const { result } = renderHook(() => usePosterStyleDrafts(config()));

    act(() => result.current.changeOverlay({ blur_amount: 20 }));
    act(() => result.current.changeOverlay({ border_enabled: false }));

    expect(result.current.overlayOptions).toEqual({ border_enabled: false, blur_amount: 20 });
  });

  it('keeps an edited value when the global config changes underneath it', () => {
    const { result, rerender } = renderHook(({ c }) => usePosterStyleDrafts(c), {
      initialProps: { c: config() },
    });

    act(() => result.current.changeOverlay({ blur_amount: 20 }));
    rerender({ c: config({ overlay_options: { border_enabled: true, blur_amount: 99 } }) });

    expect(result.current.overlayOptions).toEqual({ border_enabled: true, blur_amount: 20 });
  });

  it('edits the three option sets independently', () => {
    const { result } = renderHook(() => usePosterStyleDrafts(config()));

    act(() => result.current.changeText({ all_caps: true }));

    expect(result.current.textOptions).toEqual({ font_name: 'Serif.ttf', all_caps: true });
    expect(result.current.overlayOptions).toEqual({ border_enabled: true, blur_amount: 50 });
    expect(result.current.quality).toBe(85);
  });

  it('ignores an edit made before the config could provide a base', () => {
    const { result } = renderHook(() => usePosterStyleDrafts(null));

    act(() => result.current.changeOverlay({ blur_amount: 20 }));

    expect(result.current.overlayOptions).toBeUndefined();
  });

  it('goes back to following the config on reset, not to a copy of it', () => {
    const { result, rerender } = renderHook(({ c }) => usePosterStyleDrafts(c), {
      initialProps: { c: config() },
    });
    act(() => result.current.changeOverlay({ blur_amount: 20 }));
    act(() => result.current.changeQuality(50));

    act(() => result.current.reset());
    rerender({ c: config({ overlay_options: { border_enabled: true, blur_amount: 99 } }) });

    expect(result.current.overlayOptions).toEqual({ border_enabled: true, blur_amount: 99 });
    expect(result.current.quality).toBe(85);
  });
});
