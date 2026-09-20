import type { ItemStats } from '../../types';

export function coveragePercent(stats: ItemStats): number {
  if (stats.total === 0) return 0;
  return Math.round((stats.processed / stats.total) * 100);
}

export function failedPercent(stats: ItemStats): number {
  if (stats.total === 0) return 0;
  return (stats.errors / stats.total) * 100;
}

export function coverageLine(stats: ItemStats): string {
  const format = (n: number) => n.toLocaleString();
  const parts = [`${format(stats.processed)} of ${format(stats.total)} have a poster`];
  if (stats.errors > 0) parts.push(`${format(stats.errors)} failed`);
  return parts.join(' · ');
}
