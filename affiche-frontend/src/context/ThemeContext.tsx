import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

import {
  applyTheme,
  prefersDark,
  readStoredTheme,
  resolveTheme,
  storeTheme,
  watchSystemTheme,
  type ResolvedTheme,
  type ThemePreference,
} from '../theme';

interface ThemeContextValue {

  preference: ThemePreference;

  resolved: ResolvedTheme;
  setPreference: (preference: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(readStoredTheme);
  const [systemPrefersDark, setSystemPrefersDark] = useState(prefersDark);

  const resolved = resolveTheme(preference, systemPrefersDark);

  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
  }, [resolved]);

  useEffect(() => watchSystemTheme(setSystemPrefersDark), []);

  const setPreference = (next: ThemePreference) => {
    setPreferenceState(next);
    storeTheme(next);
    applyTheme(next);
  };

  return (
    <ThemeContext.Provider value={{ preference, resolved, setPreference }}>
      {children}
    </ThemeContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('useTheme must be used within a ThemeProvider');
  return value;
}
