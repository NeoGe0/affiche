import { useEffect, useEffectEvent, useRef, useState } from 'react';

import { dashboardApi, errorMessage } from '../api';
import type { DashboardSummary } from '../types';

export function useDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const latestRequest = useRef(0);

  const fetchSummary = useEffectEvent(async () => {
    const request = ++latestRequest.current;
    try {
      const next = await dashboardApi.getSummary();
      if (request !== latestRequest.current) return;
      setSummary(next);
      setError(null);
    } catch (e) {
      if (request !== latestRequest.current) return;
      setError(errorMessage(e, 'Failed to load the dashboard.'));
    }
  });

  useEffect(() => {
    void fetchSummary();
  }, [refreshToken]);

  return {
    summary,
    error,

    isLoading: summary === null && error === null,
    reload: () => setRefreshToken((n) => n + 1),
  };
}
