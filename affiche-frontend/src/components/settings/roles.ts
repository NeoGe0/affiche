import type { UserRole } from '../../types';

export const ROLE_LABEL: Record<UserRole, string> = {
  ADMIN: 'Admin',
  OPERATOR: 'Operator',
};

export const ROLE_SUMMARY: Record<UserRole, string> = {
  ADMIN: 'Everything, including settings, media servers, poster providers and accounts.',
  OPERATOR: 'Browse libraries and work on posters — sync, generate, upload, reset. No settings, no accounts.',
};
