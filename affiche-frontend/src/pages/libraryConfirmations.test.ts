import { describe, expect, it } from 'vitest';

import { confirmationCopy, type ConfirmAction } from './libraryConfirmations';

const ctx = { libraryName: 'Movies', itemName: 'Alien', selectionCount: 3 };

describe('confirmationCopy', () => {
  it('names the library in library-scoped actions', () => {
    expect(confirmationCopy('generate', ctx).message).toContain('Movies');
    expect(confirmationCopy('upload', ctx).message).toContain('Movies');
  });

  it('names the item in item-scoped actions', () => {
    expect(confirmationCopy('item-reset', ctx).message).toContain('"Alien"');
  });

  it('marks exactly the destructive actions as danger', () => {
    const actions: ConfirmAction[] = [
      'generate', 'upload', 'reset', 'item-reset',
      'selection-generate', 'selection-upload', 'selection-reset', 'empty-trash',
    ];
    const danger = actions.filter((a) => confirmationCopy(a, ctx).variant === 'danger');

    expect(danger).toEqual(['reset', 'item-reset', 'selection-reset', 'empty-trash']);
  });

  it('offers the unprocessed opt-in only on the library-wide reset', () => {
    expect(confirmationCopy('reset', ctx).checkboxLabel).toBe('Also reset items with no poster yet');
    expect(confirmationCopy('item-reset', ctx).checkboxLabel).toBeUndefined();
    expect(confirmationCopy('generate', ctx).checkboxLabel).toBeUndefined();
  });

  it('counts the selection in every bulk action, so the number is confirmed not assumed', () => {
    for (const [action, verb] of [
      ['selection-generate', 'Generate'], ['selection-upload', 'Upload'], ['selection-reset', 'Reset'],
    ] as const) {
      const { message, confirmLabel } = confirmationCopy(action, ctx);
      expect(message).toContain('3 selected items');
      expect(confirmLabel).toBe(`${verb} 3`);
    }
  });

  it('keeps the bulk wording singular for one item', () => {
    expect(confirmationCopy('selection-reset', { ...ctx, selectionCount: 1 }).message)
      .toContain('1 selected item,');
  });

  it('says an upload replaces the media server artwork and that Reset brings it back', () => {
    for (const action of ['upload', 'selection-upload'] as const) {
      const { message } = confirmationCopy(action, ctx);
      expect(message).toMatch(/replacing the artwork/);
      expect(message).toMatch(/Reset puts it back/);
    }
  });

  it('tells generate where the new posters end up, per the library upload setting', () => {
    expect(confirmationCopy('generate', { ...ctx, uploadsAutomatically: false }).message)
      .toMatch(/stay in Affiche until you upload/);
    expect(confirmationCopy('generate', { ...ctx, uploadsAutomatically: true }).message)
      .toMatch(/uploads automatically.*Reset puts it back/);
    expect(confirmationCopy('generate', ctx).message)
      .toMatch(/Libraries that upload automatically/);
  });

  it('names the upload in the generate button when the library uploads automatically', () => {
    expect(confirmationCopy('generate', { ...ctx, uploadsAutomatically: true }).confirmLabel).toBe('Generate & upload');
    expect(confirmationCopy('generate', { ...ctx, uploadsAutomatically: false }).confirmLabel).toBe('Generate');
  });

  it('quotes the pending count on generate only when the page has one', () => {
    expect(confirmationCopy('generate', { ...ctx, pendingCount: 354 }).message).toContain('(354)');
    expect(confirmationCopy('generate', ctx).message).not.toMatch(/\(\d+\)/);
  });

  it('states that emptying the trash never touches the media server', () => {
    const { message } = confirmationCopy('empty-trash', ctx);

    expect(message).toMatch(/media server is never touched/i);
    expect(message).toMatch(/cannot be undone/i);
  });
});

describe('reset wording', () => {
  it('describes Reset as putting the original back, not as something that cannot be undone', () => {
    for (const action of ['reset', 'item-reset', 'selection-reset'] as const) {
      const { message } = confirmationCopy(action, ctx);
      expect(message).toMatch(/puts back/);
      expect(message).not.toMatch(/cannot be undone/);
    }
  });
});
