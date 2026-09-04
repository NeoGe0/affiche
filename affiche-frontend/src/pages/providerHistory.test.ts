import { describe, expect, it } from 'vitest';

import {
  labelledDays,
  linePath,
  nearestIndex,
  toIsoDay,
  toSeries,
  windowDays,
  xAt,
  yAt,
  yMax,
  yTicks,
} from './providerHistory';
import type { ProviderDay } from '../types';

const BOX = { width: 100, height: 50 };
const day = (day: string, provider: string, count: number): ProviderDay => ({ day, provider, count });

describe('windowDays', () => {
  it('ends on today and runs oldest first', () => {
    const days = windowDays(3, new Date(2026, 7, 28));

    expect(days).toEqual(['2026-08-26', '2026-08-27', '2026-08-28']);
  });

  it('spans a month boundary', () => {
    expect(windowDays(2, new Date(2026, 8, 1))).toEqual(['2026-08-31', '2026-09-01']);
  });

  it('uses the local date, not UTC', () => {

    const lateEvening = new Date(2026, 7, 28, 23, 30);

    expect(toIsoDay(lateEvening)).toBe('2026-08-28');
  });
});

describe('toSeries', () => {
  const days = ['2026-08-26', '2026-08-27', '2026-08-28'];

  it('pads a quiet day with zero rather than leaving a gap', () => {

    const series = toSeries([day('2026-08-26', 'tmdb', 2), day('2026-08-28', 'tmdb', 1)], days);

    expect(series[0].values).toEqual([2, 0, 1]);
  });

  it('gives every provider the same number of points', () => {
    const series = toSeries([day('2026-08-26', 'tmdb', 2), day('2026-08-28', 'fanart', 1)], days);

    expect(series.map((s) => s.values.length)).toEqual([3, 3]);
  });

  it('ranks the providers by window total, largest first', () => {
    const series = toSeries(
      [day('2026-08-26', 'fanart', 1), day('2026-08-27', 'tmdb', 5)],
      days
    );

    expect(series.map((s) => s.provider)).toEqual(['tmdb', 'fanart']);
  });

  it('breaks a tie by name, so the order and the colours are stable', () => {
    const series = toSeries([day('2026-08-26', 'tmdb', 1), day('2026-08-26', 'fanart', 1)], days);

    expect(series.map((s) => s.provider)).toEqual(['fanart', 'tmdb']);
  });

  it('totals a provider across the window', () => {
    const series = toSeries(
      [day('2026-08-26', 'tmdb', 2), day('2026-08-28', 'tmdb', 3)],
      days
    );

    expect(series[0].total).toBe(5);
  });

  it('ignores a day outside the window rather than misplacing it', () => {
    const series = toSeries([day('2026-01-01', 'tmdb', 9), day('2026-08-27', 'tmdb', 1)], days);

    expect(series[0].values).toEqual([0, 1, 0]);
    expect(series[0].total).toBe(1);
  });

  it('has no series at all when nothing was generated', () => {
    expect(toSeries([], days)).toEqual([]);
  });
});

describe('yMax', () => {
  it('never returns zero, so an empty window still draws an axis', () => {
    expect(yMax([{ provider: 'tmdb', values: [0, 0], total: 0 }])).toBe(1);
    expect(yMax([])).toBe(1);
  });

  it('clears the tallest point rather than clipping it', () => {
    expect(yMax([{ provider: 'tmdb', values: [0, 42], total: 42 }])).toBeGreaterThanOrEqual(42);
  });

  it('rounds up to a value a human would pick', () => {
    expect(yMax([{ provider: 'tmdb', values: [42], total: 42 }])).toBe(50);
    expect(yMax([{ provider: 'tmdb', values: [7], total: 7 }])).toBe(7);
    expect(yMax([{ provider: 'tmdb', values: [130], total: 130 }])).toBe(200);
  });

  it('takes the peak across every series, not just the first', () => {
    expect(yMax([
      { provider: 'a', values: [1], total: 1 },
      { provider: 'b', values: [9], total: 9 },
    ])).toBe(9);
  });
});

describe('yTicks', () => {
  it('runs from zero to the top inclusive', () => {
    expect(yTicks(100, 4)).toEqual([0, 25, 50, 75, 100]);
  });

  it('gives whole numbers — half a poster is not a thing', () => {
    expect(yTicks(10, 4).every(Number.isInteger)).toBe(true);
  });
});

describe('plotting', () => {
  it('pins the first and last day to the ends of the plot', () => {
    expect(xAt(0, 3, BOX)).toBe(0);
    expect(xAt(2, 3, BOX)).toBe(100);
  });

  it('centres a single-day window instead of pinning it to the left edge', () => {
    expect(xAt(0, 1, BOX)).toBe(50);
  });

  it('puts zero on the baseline and the max at the top', () => {

    expect(yAt(0, 10, BOX)).toBe(50);
    expect(yAt(10, 10, BOX)).toBe(0);
  });

  it('draws one command per point, starting with a move', () => {
    const path = linePath([0, 5, 10], 10, BOX);

    expect(path.startsWith('M')).toBe(true);
    expect(path.match(/L/g)).toHaveLength(2);
  });
});

describe('nearestIndex', () => {
  it('snaps to the closest day, so the reader aims at a date not a line', () => {
    expect(nearestIndex(0, 3, BOX)).toBe(0);
    expect(nearestIndex(49, 3, BOX)).toBe(1);
    expect(nearestIndex(100, 3, BOX)).toBe(2);
  });

  it('clamps a pointer that leaves the plot', () => {
    expect(nearestIndex(-40, 3, BOX)).toBe(0);
    expect(nearestIndex(400, 3, BOX)).toBe(2);
  });
});

describe('labelledDays', () => {
  it('labels every day when they all fit', () => {
    expect(labelledDays(5, 6).size).toBe(5);
  });

  it('thins a long window instead of smearing the labels together', () => {
    expect(labelledDays(90, 6).size).toBeLessThanOrEqual(7);
  });

  it('always keeps the first and the last — they say what window this is', () => {
    const labelled = labelledDays(90, 6);

    expect(labelled.has(0)).toBe(true);
    expect(labelled.has(89)).toBe(true);
  });
});
