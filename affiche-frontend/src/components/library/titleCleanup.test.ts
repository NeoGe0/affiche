import { describe, expect, it } from 'vitest';

import type { TitleProposal } from '../../types';
import {
  approveLabel, checkFraction, checkProgressLine, initialSelection, pendingCount, runSummary,
  summaryLine, toggle, toggleAll,
} from './titleCleanup';

const row = (item_id: number, status: TitleProposal['status'] = 'pending'): TitleProposal => ({
  item_id,
  current_title: `Current ${item_id}`,
  proposed_title: `Proposed ${item_id}`,
  provider: 'tmdb',
  status,
});

describe('initialSelection', () => {
  it('ticks every pending row, because the list is the answer not the question', () => {
    expect([...initialSelection([row(1), row(2)])]).toEqual([1, 2]);
  });

  it('never ticks a row a run has already finished', () => {
    const selected = initialSelection([row(1), row(2, 'renamed'), row(3, 'failed')]);
    expect([...selected]).toEqual([1]);
  });
});

describe('toggle', () => {
  it('unticks a ticked row and ticks an unticked one', () => {
    expect([...toggle(new Set([1, 2]), 2)]).toEqual([1]);
    expect([...toggle(new Set([1]), 2)]).toEqual([1, 2]);
  });

  it('returns a new set, so the panel re-renders', () => {
    const before = new Set([1]);
    expect(toggle(before, 2)).not.toBe(before);
    expect([...before]).toEqual([1]);
  });
});

describe('toggleAll', () => {
  const proposals = [row(1), row(2), row(3, 'renamed')];

  it('clears the selection when everything pending is already ticked', () => {
    expect([...toggleAll(proposals, new Set([1, 2]))]).toEqual([]);
  });

  it('ticks every pending row from a partial selection', () => {
    expect([...toggleAll(proposals, new Set([1]))]).toEqual([1, 2]);
  });

  it('does not tick finished rows when selecting all', () => {
    expect(toggleAll(proposals, new Set()).has(3)).toBe(false);
  });
});

describe('approveLabel', () => {
  it('counts what is selected, in words', () => {
    expect(approveLabel(0)).toBe('Rename');
    expect(approveLabel(1)).toBe('Rename 1 item');
    expect(approveLabel(6)).toBe('Rename 6 items');
  });
});

describe('summaryLine', () => {
  it('names the library and counts the disagreements', () => {
    expect(summaryLine([row(1), row(2)], 'Films FR')).toContain('2 titles in Films FR');
  });

  it('reads as a sentence for a single row', () => {
    expect(summaryLine([row(1)], 'Films FR')).toContain('1 title in Films FR');
  });

  it('says plainly when nothing disagrees', () => {
    expect(summaryLine([], 'Films FR')).toMatch(/^No titles in Films FR/);
  });

  it('does not count rows a run has finished as still disagreeing', () => {
    expect(summaryLine([row(1, 'renamed')], 'Films FR')).toMatch(/^No titles/);
  });
});

describe('runSummary', () => {
  it('is silent until something has run', () => {
    expect(runSummary([row(1), row(2)])).toBeNull();
  });

  it('reports what a finished run did', () => {
    expect(runSummary([row(1, 'renamed'), row(2, 'renamed')])).toBe('2 renamed');
  });

  it('reports failures beside the renames', () => {
    expect(runSummary([row(1, 'renamed'), row(2, 'failed')])).toBe('1 renamed, 1 could not be');
  });
});

describe('pendingCount', () => {
  it('counts only what can still be approved', () => {
    expect(pendingCount([row(1), row(2, 'renamed'), row(3, 'failed')])).toBe(1);
  });
});

describe('checkProgressLine', () => {
  const running = { running: true, checked: 12, total: 40, mismatched: 2 };

  it('is silent when no check is running', () => {
    expect(checkProgressLine({ ...running, running: false })).toBeNull();
  });

  it('counts both how far it has got and what it has found', () => {
    expect(checkProgressLine(running)).toBe('Checking 12 of 40 — 2 to fix so far');
  });

  it('reads as a sentence for a single find', () => {
    expect(checkProgressLine({ ...running, mismatched: 1 })).toContain('1 to fix so far');
  });
});

describe('checkFraction', () => {
  it('is zero before a total is known, rather than NaN', () => {
    expect(checkFraction({ running: true, checked: 0, total: 0, mismatched: 0 })).toBe(0);
  });

  it('is the share checked so far', () => {
    expect(checkFraction({ running: true, checked: 10, total: 40, mismatched: 0 })).toBe(0.25);
  });

  it('never exceeds one', () => {
    expect(checkFraction({ running: true, checked: 50, total: 40, mismatched: 0 })).toBe(1);
  });
});
