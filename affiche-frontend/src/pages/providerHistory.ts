import type { ProviderDay } from '../types';

export interface ProviderSeries {
  provider: string;

  values: number[];

  total: number;
}

export function windowDays(days: number, today: Date = new Date()): string[] {
  const result: string[] = [];
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const day = new Date(today);
    day.setDate(day.getDate() - offset);
    result.push(toIsoDay(day));
  }
  return result;
}

export function toIsoDay(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

export function toSeries(rows: ProviderDay[], days: string[]): ProviderSeries[] {
  const byProvider = new Map<string, Map<string, number>>();
  for (const row of rows) {
    const counts = byProvider.get(row.provider) ?? new Map<string, number>();
    counts.set(row.day, (counts.get(row.day) ?? 0) + row.count);
    byProvider.set(row.provider, counts);
  }

  return [...byProvider.entries()]
    .map(([provider, counts]) => {
      const values = days.map((day) => counts.get(day) ?? 0);
      return { provider, values, total: values.reduce((sum, value) => sum + value, 0) };
    })
    .sort((a, b) => b.total - a.total || a.provider.localeCompare(b.provider));
}

export function yMax(series: ProviderSeries[]): number {
  const peak = Math.max(1, ...series.flatMap((s) => s.values));
  const magnitude = 10 ** Math.floor(Math.log10(peak));
  return Math.ceil(peak / magnitude) * magnitude;
}

export function yTicks(max: number, count = 4): number[] {
  return Array.from({ length: count + 1 }, (_, i) => Math.round((max / count) * i));
}

export interface PlotBox {
  width: number;
  height: number;
}

export function xAt(index: number, dayCount: number, box: PlotBox): number {
  if (dayCount <= 1) return box.width / 2;
  return (index / (dayCount - 1)) * box.width;
}

export function yAt(value: number, max: number, box: PlotBox): number {
  return box.height - (value / max) * box.height;
}

export function linePath(values: number[], max: number, box: PlotBox): string {
  return values
    .map((value, index) => {
      const command = index === 0 ? 'M' : 'L';
      return `${command}${xAt(index, values.length, box).toFixed(2)} ${yAt(value, max, box).toFixed(2)}`;
    })
    .join(' ');
}

export function nearestIndex(x: number, dayCount: number, box: PlotBox): number {
  if (dayCount <= 1) return 0;
  const ratio = Math.min(Math.max(x / box.width, 0), 1);
  return Math.round(ratio * (dayCount - 1));
}

export function shortDay(isoDay: string): string {
  const [year, month, day] = isoDay.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

export function labelledDays(dayCount: number, target = 6): Set<number> {
  if (dayCount <= target) return new Set(Array.from({ length: dayCount }, (_, i) => i));
  const step = Math.ceil((dayCount - 1) / (target - 1));
  const indices = new Set<number>();
  for (let i = 0; i < dayCount - 1; i += step) indices.add(i);
  indices.add(dayCount - 1);
  return indices;
}
