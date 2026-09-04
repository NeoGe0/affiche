import { describe, expect, it } from 'vitest';

import type { Collection } from '../../types';
import { memberSummary } from './collectionSummary';

const collection = (member_count: number, child_count?: number | null): Collection => ({
  id: 1, library_id: 2, title: 'Saga', member_count, child_count,
  processed: false, locked: false,
});

describe('memberSummary', () => {
  it('reports the count Affiche knows when the server agrees', () => {
    expect(memberSummary(collection(3, 3))).toBe('3 items');
  });

  it('reports both when the server holds more than Affiche has synced', () => {
    expect(memberSummary(collection(2, 5))).toBe('2 items of 5');
  });

  it('says nothing extra when the server reports no count at all', () => {
    expect(memberSummary(collection(4, null))).toBe('4 items');
    expect(memberSummary(collection(4))).toBe('4 items');
  });

  it('does not report a server count lower than ours', () => {

    expect(memberSummary(collection(3, 1))).toBe('3 items');
  });

  it('keeps the wording singular for one item', () => {
    expect(memberSummary(collection(1, 1))).toBe('1 item');
    expect(memberSummary(collection(1, 9))).toBe('1 item of 9');
  });

  it('groups the digits on a large collection', () => {
    expect(memberSummary(collection(1234, 5678))).toBe('1,234 items of 5,678');
  });
});
