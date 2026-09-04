import { api } from './client';
import type { DashboardSummary, ProviderHistory } from '../types';

export const dashboardApi = {

  getSummary: (recentTasks?: number) => {
    const params = recentTasks === undefined ? '' : `?recent_tasks=${recentTasks}`;
    return api.get<DashboardSummary>(`/dashboard${params}`);
  },

  getProviderHistory: (days: number, libraryId?: number) => {
    const params = new URLSearchParams({ days: String(days) });
    if (libraryId !== undefined) params.set('library_id', String(libraryId));
    return api.get<ProviderHistory>(`/dashboard/provider-history?${params}`);
  },
};
