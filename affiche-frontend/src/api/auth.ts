import { api } from './client';
import type { AuthStatus, UserAccount, UserResponse, UserRole } from '../types';

export const authApi = {
  status: () => api.get<AuthStatus>('/auth/status'),
  setup: (username: string, password: string) =>
    api.post<UserResponse>('/auth/setup', { username, password }),
  login: (username: string, password: string) =>
    api.post<UserResponse>('/auth/login', { username, password }),
  logout: () => api.post<{ status: string }>('/auth/logout'),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<UserResponse>('/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  me: () => api.get<UserResponse>('/auth/me'),

  listUsers: () => api.get<UserAccount[]>('/auth/users'),
  createUser: (username: string, password: string, role: UserRole) =>
    api.post<UserAccount>('/auth/users', { username, password, role }),
  setUserRole: (id: number, role: UserRole) =>
    api.patch<UserAccount>(`/auth/users/${id}`, { role }),
  deleteUser: (id: number) => api.delete(`/auth/users/${id}`),
};
