import { describe, expect, it } from 'vitest';

import type { DashboardTask, ItemStats } from '../types';
import {
  byCoverageAscending, coveragePercent, providerBarPercent, taskLabel, taskTimestamp,
} from './dashboardStats';

const stats = (overrides: Partial<ItemStats> = {}): ItemStats => ({
  total: 0, processed: 0, unprocessed: 0, errors: 0, locked: 0, uploaded: 0, ...overrides,
});

const task = (overrides: Partial<DashboardTask> = {}): DashboardTask => ({
  task_id: 't', status: 'completed', ...overrides,
});

describe('coveragePercent', () => {
  it('is the share of items with a generated poster', () => {
    expect(coveragePercent(stats({ total: 200, processed: 50 }))).toBe(25);
  });

  it('reports an empty library as 0%, not 100%', () => {

    expect(coveragePercent(stats())).toBe(0);
  });

  it('rounds rather than truncating', () => {
    expect(coveragePercent(stats({ total: 3, processed: 2 }))).toBe(67);
  });
});

describe('byCoverageAscending', () => {
  it('puts the least-covered library first', () => {
    const rows = [
      { name: 'done', stats: stats({ total: 10, processed: 10 }) },
      { name: 'behind', stats: stats({ total: 10, processed: 1 }) },
      { name: 'half', stats: stats({ total: 10, processed: 5 }) },
    ];

    expect(byCoverageAscending(rows).map((r) => r.name)).toEqual(['behind', 'half', 'done']);
  });

  it('breaks a tie on size, so the bigger backlog leads', () => {
    const rows = [
      { name: 'small', stats: stats({ total: 5 }) },
      { name: 'big', stats: stats({ total: 500 }) },
    ];

    expect(byCoverageAscending(rows).map((r) => r.name)).toEqual(['big', 'small']);
  });

  it('does not mutate the array it was given', () => {
    const rows = [
      { stats: stats({ total: 10, processed: 10 }) },
      { stats: stats({ total: 10, processed: 1 }) },
    ];
    const before = [...rows];

    byCoverageAscending(rows);

    expect(rows).toEqual(before);
  });
});

describe('providerBarPercent', () => {
  it('scales against the widest provider', () => {
    expect(providerBarPercent(25, 50)).toBe(50);
    expect(providerBarPercent(50, 50)).toBe(100);
  });

  it('is 0 rather than NaN when there is nothing to scale against', () => {
    expect(providerBarPercent(0, 0)).toBe(0);
  });
});

describe('taskLabel', () => {
  it('reads the backend task-name prefixes', () => {
    expect(taskLabel(task({ task_name: 'library_sync_1_2' }))).toBe('Library sync');
    expect(taskLabel(task({ task_name: 'poster_sync_2' }))).toBe('Poster generation');
    expect(taskLabel(task({ task_name: 'poster_reset_2' }))).toBe('Poster reset');
    expect(taskLabel(task({ task_name: 'poster_upload_2' }))).toBe('Poster upload');
  });

  it('falls back to the raw name for a task it does not know', () => {
    expect(taskLabel(task({ task_name: 'something_new' }))).toBe('something_new');
  });

  it('never renders an empty label', () => {
    expect(taskLabel(task({ task_name: null }))).toBe('Task');
  });
});

describe('taskTimestamp', () => {
  it('prefers when the task ended', () => {
    expect(taskTimestamp(task({ created_at: 'a', completed_at: 'b' }))).toBe('b');
  });

  it('falls back to when it started for a task still running', () => {
    expect(taskTimestamp(task({ created_at: 'a', status: 'running' }))).toBe('a');
  });

  it('is null when neither is known', () => {
    expect(taskTimestamp(task())).toBeNull();
  });
});
