import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { authApi } from '../api';
import { UNAUTHORIZED_EVENT } from '../api/client';
import type { AuthStatus, UserRole } from '../types';

interface AuthContextValue {

  status: AuthStatus | null;
  loading: boolean;
  username: string | null;
  role: UserRole | null;

  isAdmin: boolean;
  isAuthenticated: boolean;
  setupRequired: boolean;

  passwordChangeRequired: boolean;
  login: (username: string, password: string) => Promise<void>;
  setup: (username: string, password: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const next = await authApi.status();
      setStatus(next);
    } catch {

      setStatus({ setup_required: false, authenticated: false, password_change_required: false });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const onUnauthorized = () => {
      setStatus(prev =>
        prev ? { ...prev, authenticated: false, username: null } : prev
      );
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    await authApi.login(username, password);
    await refresh();
  }, [refresh]);

  const setup = useCallback(async (username: string, password: string) => {
    await authApi.setup(username, password);
    await refresh();
  }, [refresh]);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    await authApi.changePassword(currentPassword, newPassword);
    await refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      await refresh();
    }
  }, [refresh]);

  const value: AuthContextValue = useMemo(
    () => ({
      status,
      loading,
      username: status?.username ?? null,
      role: status?.role ?? null,
      isAdmin: status?.role === 'ADMIN',
      isAuthenticated: !!status?.authenticated,
      setupRequired: !!status?.setup_required,
      passwordChangeRequired: !!status?.password_change_required,
      login,
      setup,
      changePassword,
      logout,
      refresh,
    }),
    [status, loading, login, setup, changePassword, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
