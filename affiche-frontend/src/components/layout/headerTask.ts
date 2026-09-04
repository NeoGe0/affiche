import type { TaskKind } from '../../types';

const RUNNING_VERB: Partial<Record<TaskKind, string>> = {
  sync: 'Syncing',
  generate: 'Generating',
  reset: 'Resetting',
};

export function runningTaskVerb(taskKind: TaskKind | null | undefined): string | null {
  return (taskKind && RUNNING_VERB[taskKind]) ?? null;
}

export function runningActionLabel(
  taskKind: TaskKind | null | undefined,
  pct: number | null
): string | null {
  if (!taskKind) return null;
  const verb = runningTaskVerb(taskKind);
  if (!verb) return 'Working…';
  return pct == null ? `${verb}…` : `${verb}… ${pct}%`;
}
