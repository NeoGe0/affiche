import { Copy, RotateCw, Send, Webhook } from 'lucide-react';

import type { MediaServerType } from '../../types';
import { webhookUrl } from './mediaServerState';
import sectionStyles from './SettingsSection.module.css';
import styles from './WebhookPanel.module.css';

const SETUP_HINT: Record<MediaServerType, string> = {
  PLEX: 'Plex Pass (Settings → Webhooks)',
  JELLYFIN: 'the Jellyfin Webhook plugin (send the ItemAdded event)',
};

interface WebhookPanelProps {
  serverType: MediaServerType;
  enabled: boolean;

  token: string | null;
  isBusy: boolean;
  onToggle: (enabled: boolean) => void;

  onCopy: (url: string) => void;
  onTest: () => void;
  onRegenerate: () => void;
}

export function WebhookPanel({
  serverType,
  enabled,
  token,
  isBusy,
  onToggle,
  onCopy,
  onTest,
  onRegenerate,
}: WebhookPanelProps) {
  const url = token ? webhookUrl(window.location.origin, token) : null;

  return (
    <div className={sectionStyles.divider}>
      <div className={styles.header}>
        <Webhook size={16} className={styles.icon} />
        <span className={styles.title}>Webhooks</span>
      </div>
      <p className={styles.description}>
        Instant pickup of new items. Requires {SETUP_HINT[serverType]}. Each library uses its
        configured auto-pickup action.
      </p>
      <label className={`${sectionStyles.toggle} ${styles.toggle}`}>
        <input
          type="checkbox"
          checked={enabled}
          disabled={isBusy}
          onChange={(e) => onToggle(e.target.checked)}
        />
        <span>Enable webhooks</span>
      </label>

      {enabled && url && (
        <div className={styles.details}>
          <div className={styles.urlRow}>
            <code className={styles.url}>{url}</code>
            <button
              type="button"
              onClick={() => onCopy(url)}
              title="Copy URL"
              className={sectionStyles.outlineButton}
            >
              <Copy size={14} /> Copy
            </button>
          </div>
          <div className={styles.actions}>
            <button
              type="button"
              onClick={onTest}
              disabled={isBusy}
              title="Simulate a new-item webhook (dry-run) and watch the app log"
              className={`${sectionStyles.outlineButton} ${sectionStyles.outlineButtonSmall} ${sectionStyles.outlineButtonAccent}`}
            >
              <Send size={13} /> Send test
            </button>
            <button
              type="button"
              onClick={onRegenerate}
              disabled={isBusy}
              className={`${sectionStyles.outlineButton} ${sectionStyles.outlineButtonSmall} ${sectionStyles.outlineButtonMuted}`}
            >
              <RotateCw size={13} /> Regenerate URL
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
