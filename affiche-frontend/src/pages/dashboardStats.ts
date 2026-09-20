import { coveragePercent } from '../components/library/coverage';
import type { DashboardTask, ItemStats } from '../types';

export { coveragePercent };

export function byCoverageAscending<T extends { stats: ItemStats }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => {
    const diff = coveragePercent(a.stats) - coveragePercent(b.stats);
    return diff !== 0 ? diff : b.stats.total - a.stats.total;
  });
}

export function providerBarPercent(count: number, max: number): number {
  return max === 0 ? 0 : Math.round((count / max) * 100);
}

const TASK_LABELS: [RegExp, string][] = [
  [/^library_sync/, 'Library sync'],
  [/^poster_sync/, 'Poster generation'],
  [/^poster_reset/, 'Poster reset'],
  [/^poster_upload/, 'Poster upload'],
];

export function taskLabel(task: DashboardTask): string {
  const name = task.task_name ?? '';
  return TASK_LABELS.find(([pattern]) => pattern.test(name))?.[1] ?? (name || 'Task');
}

export function taskTimestamp(task: DashboardTask): string | null {
  return task.completed_at ?? task.created_at ?? null;
}

const TASK_STATUS_LABELS: Record<string, string> = {
  pending: 'Queued',
  running: 'Running',
  completed: 'Done',
  failed: 'Failed',
  cancelled: 'Stopped',
};

export function taskStatusLabel(status: string): string {
  return TASK_STATUS_LABELS[status] ?? status;
}
