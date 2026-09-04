import { useEffect, useEffectEvent, useRef, useState } from 'react';

import { dashboardApi, errorMessage } from '../api';
import type { ProviderHistory } from '../types';

export const WINDOW_PRESETS = [7, 30, 90] as const;
export const DEFAULT_WINDOW = 30;

export function useProviderHistory(initialDays: number = DEFAULT_WINDOW) {
  const [days, setDays] = useState(initialDays);
  const [history, setHistory] = useState<ProviderHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);
  const latestRequest = useRef(0);

  const fetchHistory = useEffectEvent(async (window: number) => {
    const request = ++latestRequest.current;
    setIsRefreshing(true);
    try {
      const next = await dashboardApi.getProviderHistory(window);
      if (request !== latestRequest.current) return;
      setHistory(next);
      setError(null);
    } catch (e) {
      if (request !== latestRequest.current) return;
      setError(errorMessage(e, 'Failed to load the provider history.'));
    } finally {
      if (request === latestRequest.current) setIsRefreshing(false);
    }
  });

  useEffect(() => {
    void fetchHistory(days);
  }, [days, refreshToken]);

  return {
    history,
    days,
    setDays,
    error,

    isLoading: history === null && error === null,
    isRefreshing,
    reload: () => setRefreshToken((n) => n + 1),
  };
}
