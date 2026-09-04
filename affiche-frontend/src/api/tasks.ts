import { api } from './client';

export interface TaskProgress {
  current: number;
  total: number;
  message?: string | null;
}

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  task_name?: string;
  blocking?: boolean;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  cancelled_at?: string;
  failed_at?: string;
  message?: string;
  error?: string;
  progress?: TaskProgress | null;
  result?: Record<string, unknown>;
}

export interface CancelResponse {
  success: boolean;
  message: string;
}

export const tasksApi = {

  getTaskStatus: (taskId: string) => api.get<TaskStatus>(`/tasks/${taskId}`),

  getAllTasks: (status?: string) => {
    const params = status ? `?status=${status}` : '';
    return api.get<TaskStatus[]>(`/tasks${params}`);
  },

  getLatestTask: (taskName: string) =>
    api.get<TaskStatus | null>(`/tasks/latest/${taskName}`),

  getRunningBlockingTask: () =>
    api.get<TaskStatus | null>('/tasks/blocking/current'),

  cancelTask: (taskId: string) =>
    api.post<CancelResponse>(`/tasks/${taskId}/cancel`),
};
