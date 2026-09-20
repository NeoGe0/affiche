import { describe, expect, it } from 'vitest';

import { passwordRules } from './passwordRequirements';

describe('passwordRules', () => {
  it('needs the minimum length and a matching confirmation', () => {
    expect(passwordRules('long-enough', 'long-enough').every((r) => r.met)).toBe(true);
    expect(passwordRules('short', 'short').map((r) => r.met)).toEqual([false, true]);
    expect(passwordRules('long-enough', 'long-enougg').map((r) => r.met)).toEqual([true, false]);
  });

  it('does not call two empty fields a match', () => {
    expect(passwordRules('', '')[1].met).toBe(false);
  });
});
