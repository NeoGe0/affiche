import { describe, expect, it } from 'vitest';

import { fontChoices } from './fontChoices';

const AVAILABLE = ['Anton-Regular.ttf', 'Oswald-Regular.ttf'];

describe('fontChoices', () => {
  it('offers the available fonts unchanged when the current one is among them', () => {
    expect(fontChoices(AVAILABLE, 'Oswald-Regular.ttf')).toEqual(AVAILABLE);
  });

  it('keeps a font that is no longer installed selectable, first, so the value stays visible', () => {
    expect(fontChoices(AVAILABLE, 'Deleted-Upload.ttf')).toEqual([
      'Deleted-Upload.ttf',
      ...AVAILABLE,
    ]);
  });

  it('adds nothing when no font is selected yet', () => {
    expect(fontChoices(AVAILABLE, '')).toEqual(AVAILABLE);
  });
});
