import { describe, expect, it } from 'vitest';

import { confirmationCopy, type ConfirmAction } from './libraryConfirmations';

const ctx = { libraryName: 'Movies', itemName: 'Alien', selectionCount: 3 };

describe('confirmationCopy', () => {
  it('names the library in library-scoped actions', () => {
    expect(confirmationCopy('sync', ctx).message).toContain('Movies');
    expect(confirmationCopy('generate', ctx).message).toContain('Movies');
  });

  it('names the item in item-scoped actions', () => {
    expect(confirmationCopy('item-reset', ctx).message).toContain('"Alien"');
  });

  it('marks exactly the destructive actions as danger', () => {
    const actions: ConfirmAction[] = [
      'sync', 'generate', 'upload', 'reset', 'item-sync', 'item-generate', 'item-reset',
      'selection-reset', 'empty-trash',
    ];
    const danger = actions.filter((a) => confirmationCopy(a, ctx).variant === 'danger');

    expect(danger).toEqual(['reset', 'item-reset', 'selection-reset', 'empty-trash']);
  });

  it('offers the unprocessed opt-in only on the library-wide reset', () => {
    expect(confirmationCopy('reset', ctx).checkboxLabel).toBe('Also reset unprocessed items');
    expect(confirmationCopy('item-reset', ctx).checkboxLabel).toBeUndefined();
    expect(confirmationCopy('sync', ctx).checkboxLabel).toBeUndefined();
  });

  it('counts the selection in the bulk reset, so the number is confirmed not assumed', () => {
    const { message, confirmLabel } = confirmationCopy('selection-reset', ctx);

    expect(message).toContain('3 selected items');
    expect(confirmLabel).toBe('Reset 3');
  });

  it('keeps the bulk reset wording singular for one item', () => {
    expect(confirmationCopy('selection-reset', { ...ctx, selectionCount: 1 }).message)
      .toContain('1 selected item ');
  });

  it('states that emptying the trash never touches the media server', () => {

    const { message } = confirmationCopy('empty-trash', ctx);

    expect(message).toMatch(/media server is never touched/i);
    expect(message).toMatch(/cannot be undone/i);
  });
});
