import { describe, expect, it } from 'vitest';

import type { ItemStats } from '../../types';
import { coverageLine, failedPercent } from './coverage';

const stats = (overrides: Partial<ItemStats> = {}): ItemStats =>
  ({ total: 0, processed: 0, unprocessed: 0, errors: 0, locked: 0, uploaded: 0, ...overrides });

describe('coverageLine', () => {
  it('says how many have a poster and how many failed', () => {
    expect(coverageLine(stats({ total: 20, processed: 12, unprocessed: 6, errors: 2 })))
      .toBe('12 of 20 have a poster · 2 failed');
  });

  it('leaves failures out when there are none', () => {
    expect(coverageLine(stats({ total: 5, processed: 5 }))).toBe('5 of 5 have a poster');
  });
});

describe('failedPercent', () => {
  it('is the failed share, and 0 for an empty library', () => {
    expect(failedPercent(stats({ total: 200, errors: 5 }))).toBe(2.5);
    expect(failedPercent(stats())).toBe(0);
  });
});
