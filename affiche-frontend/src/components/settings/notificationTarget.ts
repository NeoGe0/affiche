import type { NotificationTarget, NotificationType } from '../../types';

export const NOTIFICATION_TYPES: { value: NotificationType; label: string; hint: string }[] = [
  {
    value: 'discord',
    label: 'Discord',
    hint: 'Server Settings → Integrations → Webhooks → Copy Webhook URL',
  },
  { value: 'gotify', label: 'Gotify', hint: 'https://your-gotify/message?token=…' },
  { value: 'apprise', label: 'Apprise', hint: 'Your Apprise API notify endpoint' },
  { value: 'webhook', label: 'Webhook (raw JSON)', hint: 'Any URL that accepts a POST' },
];

export function notificationTypeLabel(type: NotificationType): string {
  return NOTIFICATION_TYPES.find((t) => t.value === type)?.label ?? type;
}

export function subscribedEvents(target: NotificationTarget): string {
  const events = [
    target.on_task_completed && 'completed',
    target.on_task_failed && 'failed',
    target.on_items_errored && 'errors',
  ].filter(Boolean);
  return events.length ? events.join(', ') : 'nothing';
}

export function canSubmit(name: string, url: string, isEditing: boolean): boolean {
  if (!name.trim()) return false;
  return isEditing || Boolean(url.trim());
}
