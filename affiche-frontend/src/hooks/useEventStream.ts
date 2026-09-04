import { useEffect, useEffectEvent, useRef } from 'react';

import { API_BASE } from '../api/client';

export interface ItemProcessedEvent {
  type: 'item_processed';
  data: {
    library_id: number;
    item_id: number;
    processed: boolean;

    poster_version?: string | null;
  };
}

export interface SeasonProcessedEvent {
  type: 'season_processed';
  data: {
    library_id: number;
    item_id: number;
    season_number: number;
    processed: boolean;
    poster_version?: string | null;
  };
}

export interface TaskStatusEvent {
  type: 'task_status';
  data: {
    task_id: string;
    status: 'running' | 'completed' | 'failed' | 'cancelled';
    task_name: string;
    message?: string;
    error?: string;
  };
}

export interface LibrarySyncedEvent {
  type: 'library_synced';
  data: {
    media_server_id: number;
    library_id: number | null;
  };
}

export interface TaskProgressEvent {
  type: 'task_progress';
  data: {
    task_id: string;
    task_name: string;
    current: number;
    total: number;
    message?: string;
  };
}

export type SSEEvent = ItemProcessedEvent | SeasonProcessedEvent | TaskStatusEvent | LibrarySyncedEvent | TaskProgressEvent | { type: 'connected' };

interface UseEventStreamOptions {
  onItemProcessed?: (
    libraryId: number,
    itemId: number,
    processed: boolean,
    posterVersion?: string | null
  ) => void;
  onSeasonProcessed?: (libraryId: number, itemId: number, seasonNumber: number, processed: boolean) => void;
  onLibrarySynced?: (mediaServerId: number, libraryId: number | null) => void;
  onTaskStatus?: (taskId: string, status: string, taskName: string, message?: string, error?: string) => void;
  onTaskProgress?: (taskId: string, taskName: string, current: number, total: number, message?: string) => void;
  onConnected?: () => void;
  onError?: (error: Event) => void;
}

export function useEventStream(options: UseEventStreamOptions = {}) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const handleMessage = useEffectEvent((message: SSEEvent) => {
    switch (message.type) {
      case 'connected':
        options.onConnected?.();
        break;
      case 'item_processed':
        options.onItemProcessed?.(
          message.data.library_id,
          message.data.item_id,
          message.data.processed,
          message.data.poster_version
        );
        break;
      case 'season_processed':
        options.onSeasonProcessed?.(
          message.data.library_id,
          message.data.item_id,
          message.data.season_number,
          message.data.processed
        );
        break;
      case 'library_synced':
        options.onLibrarySynced?.(
          message.data.media_server_id,
          message.data.library_id
        );
        break;
      case 'task_status':
        options.onTaskStatus?.(
          message.data.task_id,
          message.data.status,
          message.data.task_name,
          message.data.message,
          message.data.error
        );
        break;
      case 'task_progress':
        options.onTaskProgress?.(
          message.data.task_id,
          message.data.task_name,
          message.data.current,
          message.data.total,
          message.data.message
        );
        break;
    }
  });

  const handleError = useEffectEvent((error: Event) => {
    options.onError?.(error);
  });

  useEffect(() => {

    let disposed = false;

    function connect() {
      if (disposed) return;

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const eventSource = new EventSource(`${API_BASE}/events/stream`, { withCredentials: true });
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          handleMessage(JSON.parse(event.data) as SSEEvent);
        } catch (err) {
          console.error('Failed to parse SSE message:', err);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        handleError(error);

        eventSource.close();
        eventSourceRef.current = null;
        if (disposed) return;

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = window.setTimeout(() => {
          console.log('Attempting SSE reconnection...');
          connect();
        }, 5000);
      };
    }

    connect();

    return () => {
      disposed = true;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, []);
}
