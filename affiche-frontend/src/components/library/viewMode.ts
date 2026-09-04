import type { ViewMode } from '../../types';

export const DEFAULT_VIEW_MODE: ViewMode = 'grid';

export function parseViewMode(stored: string | null): ViewMode {
  return stored === 'grid' || stored === 'list' ? stored : DEFAULT_VIEW_MODE;
}
