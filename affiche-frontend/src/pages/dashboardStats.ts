import type { DashboardTask, ItemStats } from '../types';

export function coveragePercent(stats: ItemStats): number {
  if (stats.total === 0) return 0;
  return Math.round((stats.processed / stats.total) * 100);
}

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
