import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useEventStream } from './useEventStream';

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  closed = false;

  url: string;
  init?: EventSourceInit;

  constructor(url: string, init?: EventSourceInit) {
    this.url = url;
    this.init = init;
    FakeEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  fail() {
    this.onerror?.(new Event('error'));
  }

  static get latest() {
    return FakeEventSource.instances[FakeEventSource.instances.length - 1];
  }

  static reset() {
    FakeEventSource.instances = [];
  }
}

beforeEach(() => {
  FakeEventSource.reset();
  vi.stubGlobal('EventSource', FakeEventSource);
  vi.useFakeTimers();

  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'log').mockImplementation(() => {});
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useEventStream', () => {
  it('opens one credentialed connection on mount', () => {
    renderHook(() => useEventStream({}));

    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.latest.url).toContain('/events/stream');

    expect(FakeEventSource.latest.init).toEqual({ withCredentials: true });
  });

  it('dispatches each event type to its handler', () => {
    const handlers = {
      onConnected: vi.fn(),
      onItemProcessed: vi.fn(),
      onSeasonProcessed: vi.fn(),
      onLibrarySynced: vi.fn(),
      onTaskStatus: vi.fn(),
      onTaskProgress: vi.fn(),
    };
    renderHook(() => useEventStream(handlers));
    const source = FakeEventSource.latest;

    act(() => {
      source.emit({ type: 'connected' });
      source.emit({
        type: 'item_processed',
        data: { library_id: 3, item_id: 7, processed: true, poster_version: '1a2b-3c' },
      });
      source.emit({
        type: 'season_processed',
        data: { library_id: 3, item_id: 7, season_number: 2, processed: true },
      });
      source.emit({ type: 'library_synced', data: { media_server_id: 1, library_id: 3 } });
      source.emit({
        type: 'task_status',
        data: { task_id: 't1', status: 'running', task_name: 'sync', message: 'go' },
      });
      source.emit({
        type: 'task_progress',
        data: { task_id: 't1', task_name: 'sync', current: 2, total: 10 },
      });
    });

    expect(handlers.onConnected).toHaveBeenCalledOnce();
    expect(handlers.onItemProcessed).toHaveBeenCalledWith(3, 7, true, '1a2b-3c');
    expect(handlers.onSeasonProcessed).toHaveBeenCalledWith(3, 7, 2, true);
    expect(handlers.onLibrarySynced).toHaveBeenCalledWith(1, 3);
    expect(handlers.onTaskStatus).toHaveBeenCalledWith('t1', 'running', 'sync', 'go', undefined);
    expect(handlers.onTaskProgress).toHaveBeenCalledWith('t1', 'sync', 2, 10, undefined);
  });

  it('survives a malformed message without tearing down the stream', () => {
    const onItemProcessed = vi.fn();
    renderHook(() => useEventStream({ onItemProcessed }));
    const source = FakeEventSource.latest;

    act(() => {
      source.onmessage?.({ data: 'not json' });
      source.emit({
        type: 'item_processed',
        data: { library_id: 1, item_id: 2, processed: true, poster_version: '1a2b-3c' },
      });
    });

    expect(onItemProcessed).toHaveBeenCalledWith(1, 2, true, '1a2b-3c');
  });

  it('calls the latest handlers, not the ones from the first render', () => {

    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = renderHook(({ cb }) => useEventStream({ onItemProcessed: cb }), {
      initialProps: { cb: first },
    });

    rerender({ cb: second });
    act(() => {
      FakeEventSource.latest.emit({
        type: 'item_processed',
        data: { library_id: 1, item_id: 2, processed: true, poster_version: '1a2b-3c' },
      });
    });

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledWith(1, 2, true, '1a2b-3c');
  });

  it('closes the failed connection and reconnects after 5s', () => {
    const onError = vi.fn();
    renderHook(() => useEventStream({ onError }));
    const first = FakeEventSource.latest;

    act(() => first.fail());

    expect(onError).toHaveBeenCalledOnce();
    expect(first.closed).toBe(true);
    expect(FakeEventSource.instances).toHaveLength(1);

    act(() => void vi.advanceTimersByTime(5000));

    expect(FakeEventSource.instances).toHaveLength(2);
    expect(FakeEventSource.latest).not.toBe(first);
  });

  it('does not reconnect early', () => {
    renderHook(() => useEventStream({}));

    act(() => FakeEventSource.latest.fail());
    act(() => void vi.advanceTimersByTime(4999));

    expect(FakeEventSource.instances).toHaveLength(1);
  });

  it('closes the stream on unmount', () => {
    const { unmount } = renderHook(() => useEventStream({}));
    const source = FakeEventSource.latest;

    unmount();

    expect(source.closed).toBe(true);
  });

  it('does not reconnect after unmount', () => {

    const { unmount } = renderHook(() => useEventStream({}));

    act(() => FakeEventSource.latest.fail());
    unmount();
    act(() => void vi.advanceTimersByTime(10000));

    expect(FakeEventSource.instances).toHaveLength(1);
  });
});
