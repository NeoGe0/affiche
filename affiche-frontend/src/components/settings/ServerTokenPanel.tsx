import { useState } from 'react';
import { Eye, EyeOff, KeyRound } from 'lucide-react';

import type { MediaServerType } from '../../types';
import { SERVER_CONFIG } from './mediaServerHelpers';
import sectionStyles from './SettingsSection.module.css';
import styles from './ServerTokenPanel.module.css';

interface ServerTokenPanelProps {
  serverType: MediaServerType;

  serverUrl: string;
  isBusy: boolean;

  onSubmit: (token: string) => Promise<boolean>;
}

export function ServerTokenPanel({
  serverType,
  serverUrl,
  isBusy,
  onSubmit,
}: ServerTokenPanelProps) {
  const [token, setToken] = useState('');
  const [isRevealed, setIsRevealed] = useState(false);

  const label = SERVER_CONFIG[serverType].tokenLabel;
  const canSubmit = token.trim().length > 0 && !isBusy;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    if (await onSubmit(token.trim())) {
      setToken('');
      setIsRevealed(false);
    }
  };

  return (
    <form className={sectionStyles.divider} onSubmit={handleSubmit}>
      <div className={styles.header}>
        <KeyRound size={16} className={styles.icon} />
        <span className={styles.title}>{label}</span>
      </div>
      <p className={styles.description}>
        Used for every sync and upload to {serverUrl}. Paste a new one to replace it, for instance
        after it expires or is revoked. It is checked against the server before being saved.
      </p>
      <div className={styles.row}>
        <div className={styles.inputWrapper}>
          <input
            type={isRevealed ? 'text' : 'password'}
            className={styles.input}
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder={`New ${label.toLowerCase()}`}
            aria-label={`New ${label.toLowerCase()}`}
            autoComplete="off"
            spellCheck={false}
            disabled={isBusy}
          />
          <button
            type="button"
            className={styles.reveal}
            onClick={() => setIsRevealed((shown) => !shown)}
            aria-label={isRevealed ? 'Hide what you typed' : 'Show what you typed'}
          >
            {isRevealed ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        <button
          type="submit"
          className={`${sectionStyles.outlineButton} ${sectionStyles.outlineButtonAccent}`}
          disabled={!canSubmit}
        >
          {isBusy ? 'Checking...' : 'Update'}
        </button>
      </div>
    </form>
  );
}
