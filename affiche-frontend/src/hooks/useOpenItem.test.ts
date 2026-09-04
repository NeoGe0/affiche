import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useOpenItem } from './useOpenItem';
import type { LibraryItem } from '../types';

vi.mock('../api', () => ({
  libraryApi: {},
  errorMessage: (_error: unknown, fallback: string) => fallback,
}));

vi.mock('../context/ToastContext', () => ({
  useToast: () => ({ error: vi.fn(), success: vi.fn(), info: vi.fn(), show: vi.fn() }),
}));

const alien = { id: 10, library_id: 2, title: 'Alien' } as LibraryItem;

const atScrollY = (y: number) =>
  Object.defineProperty(window, 'scrollY', { value: y, configurable: true });

const setup = () => {
  const scrollTo = vi.fn();
  window.scrollTo = scrollTo as unknown as typeof window.scrollTo;
  const { result } = renderHook(() => useOpenItem({
    allLibraries: [],
    refreshListing: vi.fn(),
    setPageBusy: vi.fn(),
    setPageMessage: vi.fn(),
  }));
  return { result, scrollTo };
};

afterEach(() => atScrollY(0));

describe('useOpenItem scroll restoration', () => {
  it('goes back to where the listing was standing', () => {
    const { result, scrollTo } = setup();
    atScrollY(1200);

    act(() => result.current.open(alien));
    atScrollY(0);
    act(() => result.current.close());

    expect(scrollTo).toHaveBeenCalledWith(0, 1200);
  });

  it('leaves the scroll alone when the listing changed underneath the item', () => {
    const { result, scrollTo } = setup();
    atScrollY(1200);

    act(() => result.current.open(alien));
    act(() => result.current.open(null));

    expect(scrollTo).not.toHaveBeenCalled();
  });

  it('remembers where the listing was, not where the detail view was', () => {

    const { result, scrollTo } = setup();
    atScrollY(1200);

    act(() => result.current.open(alien));
    atScrollY(300);
    act(() => result.current.close());

    expect(scrollTo).toHaveBeenCalledWith(0, 1200);
  });
});
