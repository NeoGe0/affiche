import { describe, expect, it } from 'vitest';

import { canSubmit, notificationTypeLabel, subscribedEvents } from './notificationTarget';
import type { NotificationTarget } from '../../types';

const target = (overrides: Partial<NotificationTarget> = {}): NotificationTarget => ({
  id: 1,
  name: 'Home',
  type: 'discord',
  url_hint: 'discord.com',
  enabled: true,
  on_task_completed: true,
  on_task_failed: true,
  on_items_errored: true,
  ...overrides,
});

describe('canSubmit', () => {
  it('requires a name either way', () => {
    expect(canSubmit('   ', 'https://x/y', false)).toBe(false);
    expect(canSubmit('   ', 'https://x/y', true)).toBe(false);
  });

  it('requires a URL to create a target', () => {
    expect(canSubmit('Home', '', false)).toBe(false);
    expect(canSubmit('Home', 'https://x/y', false)).toBe(true);
  });

  it('does not require a URL to edit one — an empty field keeps the stored credential', () => {
    expect(canSubmit('Home', '', true)).toBe(true);
  });
});

describe('subscribedEvents', () => {
  it('lists the events a target hears about', () => {
    expect(subscribedEvents(target())).toBe('completed, failed, errors');
    expect(subscribedEvents(target({ on_task_completed: false }))).toBe('failed, errors');
  });

  it('says so plainly when a target is subscribed to nothing', () => {

    expect(
      subscribedEvents(
        target({ on_task_completed: false, on_task_failed: false, on_items_errored: false })
      )
    ).toBe('nothing');
  });
});

describe('notificationTypeLabel', () => {
  it('renders the service name rather than the slug', () => {
    expect(notificationTypeLabel('gotify')).toBe('Gotify');
    expect(notificationTypeLabel('webhook')).toBe('Webhook (raw JSON)');
  });
});
