import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';

import { ToastProvider, useToast } from './ToastContext';

function Trigger() {
  const toast = useToast();
  return <button onClick={() => toast.success('Posters generated')}>go</button>;
}

afterEach(() => {
  vi.useRealTimers();
});

describe('Toasts', () => {
  it('stay while hovered, and leave once the pointer does', () => {
    vi.useFakeTimers();
    render(<ToastProvider><Trigger /></ToastProvider>);

    fireEvent.click(screen.getByText('go'));
    const toast = screen.getByRole('status');
    fireEvent.mouseEnter(toast);
    act(() => { vi.advanceTimersByTime(10_000); });
    expect(screen.getByText('Posters generated')).toBeInTheDocument();

    fireEvent.mouseLeave(toast);
    act(() => { vi.advanceTimersByTime(4_000); });
    expect(screen.queryByText('Posters generated')).not.toBeInTheDocument();
  });

  it('announce success politely and errors as alerts', () => {
    function Both() {
      const toast = useToast();
      return <button onClick={() => { toast.success('ok'); toast.error('nope'); }}>go</button>;
    }
    render(<ToastProvider><Both /></ToastProvider>);

    fireEvent.click(screen.getByText('go'));

    expect(screen.getByRole('status')).toHaveTextContent('ok');
    expect(screen.getByRole('alert')).toHaveTextContent('nope');
  });
});
