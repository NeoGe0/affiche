import { describe, expect, it } from 'vitest';

import { progressPercent, taskSummary } from './taskSummary';

describe('taskSummary', () => {
  it('reports a clean generation run without offering failures', () => {
    expect(taskSummary('generate', 'Movies', 0)).toEqual({
      title: 'Posters generated', message: 'Finished Movies.', offerFailed: false,
    });
  });

  it('counts the items a generation run left without a poster', () => {
    const summary = taskSummary('generate', 'Movies', 12);

    expect(summary.message).toContain('12 items failed');
    expect(summary.offerFailed).toBe(true);
  });

  it('keeps the failure wording singular for one item', () => {
    expect(taskSummary('generate', 'Movies', 1).message).toContain('1 item failed');
  });

  it('treats an unknown failure count as none rather than guessing', () => {
    expect(taskSummary('generate', 'All libraries').offerFailed).toBe(false);
  });

  it('names the scope for every kind of task', () => {
    for (const kind of ['sync', 'upload', 'reset', 'other'] as const) {
      expect(taskSummary(kind, 'Movies').message).toContain('Movies');
    }
  });
});

describe('progressPercent', () => {
  it('rounds and caps, and reads 0 before a total is known', () => {
    expect(progressPercent({ current: 1, total: 3 })).toBe(33);
    expect(progressPercent({ current: 5, total: 4 })).toBe(100);
    expect(progressPercent(null)).toBe(0);
    expect(progressPercent({ current: 0, total: 0 })).toBe(0);
  });
});
