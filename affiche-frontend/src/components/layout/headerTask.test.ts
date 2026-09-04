import { describe, expect, it } from 'vitest';

import { runningActionLabel, runningTaskVerb } from './headerTask';

describe('runningActionLabel', () => {
  it('leaves the button to its idle label when nothing is running', () => {
    expect(runningActionLabel(null, null)).toBeNull();
  });

  it('names the task and its progress', () => {
    expect(runningActionLabel('generate', 42)).toBe('Generating… 42%');
  });

  it('drops the percentage rather than showing a stuck 0% when the total is unknown', () => {
    expect(runningActionLabel('sync', null)).toBe('Syncing…');
  });

  it('still says something is running for a kind it has no verb for', () => {
    expect(runningActionLabel('other', 30)).toBe('Working…');
  });
});

describe('runningTaskVerb', () => {
  it('has no verb for a kind the header cannot name, so the status line stays', () => {
    expect(runningTaskVerb('other')).toBeNull();
    expect(runningTaskVerb(null)).toBeNull();
  });

  it('names the three long runs the header knows about', () => {
    expect(runningTaskVerb('reset')).toBe('Resetting');
  });
});
