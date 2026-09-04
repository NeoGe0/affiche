import { api } from './client';
import type { NotificationTarget, NotificationType } from '../types';

export interface NotificationTargetCreate {
  name: string;
  type: NotificationType;
  url: string;
  enabled?: boolean;
  on_task_completed?: boolean;
  on_task_failed?: boolean;
  on_items_errored?: boolean;
}

export type NotificationTargetUpdate = Partial<NotificationTargetCreate>;

export const notificationsApi = {
  getTargets: () => api.get<NotificationTarget[]>('/notifications'),

  createTarget: (target: NotificationTargetCreate) =>
    api.post<NotificationTarget>('/notifications', target),

  updateTarget: (targetId: number, update: NotificationTargetUpdate) =>
    api.patch<NotificationTarget>(`/notifications/${targetId}`, update),

  deleteTarget: (targetId: number) => api.delete(`/notifications/${targetId}`),

  testTarget: (targetId: number) =>
    api.post<{ delivered: boolean }>(`/notifications/${targetId}/test`, {}),

  testUrl: (target: { type: NotificationType; url: string; name?: string }) =>
    api.post<{ delivered: boolean }>('/notifications/test', target),
};
