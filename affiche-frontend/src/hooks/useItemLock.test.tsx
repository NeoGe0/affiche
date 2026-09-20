import { describe, expect, it, vi } from 'vitest';
import { act, renderHook, screen } from '@testing-library/react';
import type { ReactNode } from 'react';

import { useItemLock } from './useItemLock';
import { libraryApi } from '../api';
import { ToastProvider } from '../context/ToastContext';
import type { Library, LibraryItem } from '../types';

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  libraryApi: { setItemLock: vi.fn() },
}));

const ITEM = { id: 1, library_id: 2, title: 'Alien', locked: false } as LibraryItem;
const LIBRARIES = [{ id: 2, media_server_id: 9 } as Library];

const wrapper = ({ children }: { children: ReactNode }) => <ToastProvider>{children}</ToastProvider>;

describe('useItemLock', () => {
  it('says what a lock does once it is set, and what unlocking gives back', async () => {
    const setLock = vi.mocked(libraryApi.setItemLock);
    const { result } = renderHook(
      () => useItemLock({ allLibraries: LIBRARIES, setItems: vi.fn() }),
      { wrapper }
    );

    setLock.mockResolvedValueOnce({ ...ITEM, locked: true });
    await act(() => result.current.toggle(ITEM));
    expect(screen.getByText('Poster generation will skip "Alien" until it is unlocked.')).toBeInTheDocument();

    setLock.mockResolvedValueOnce({ ...ITEM, locked: false });
    await act(() => result.current.toggle({ ...ITEM, locked: true }));
    expect(screen.getByText('Poster generation can replace the poster for "Alien" again.')).toBeInTheDocument();
  });
});
