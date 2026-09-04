import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import { ConfigForm } from './ConfigForm';
import { providerRequiresApiKey, providerUrlMode } from '../../constants/providers';
import type { ServiceConfiguration } from '../../types';
import sectionStyles from './SettingsSection.module.css';
import styles from './PosterProviderCard.module.css';

interface PosterProviderCardProps {
  label: string;
  description: string;
  icon: React.ReactNode;
  accentColor: string;
  getKeyUrl: string;
  config: ServiceConfiguration | null;
  serviceName: string;
  defaultUrl: string;
  isSaving: boolean;
  onSave: (data: { url: string; token?: string; enabled: boolean }) => void;
  onDelete: () => void;
  onValidate: (url: string, token: string) => Promise<boolean>;
}

export function PosterProviderCard({
  label,
  description,
  icon,
  accentColor,
  getKeyUrl,
  config,
  serviceName,
  defaultUrl,
  isSaving,
  onSave,
  onDelete,
  onValidate,
}: PosterProviderCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const requiresApiKey = providerRequiresApiKey(serviceName);

  const urlMode = providerUrlMode(serviceName);
  const isConfigured = !!config?.configured || !requiresApiKey;
  const isEnabled = !!config?.enabled;

  return (
    <div className={sectionStyles.card}>
      <div className={styles.headerRow}>
      <button
        className={`${sectionStyles.cardHeader} ${styles.header}`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {}
        <span className={styles.icon} style={{ color: accentColor }}>
          {icon}
        </span>
        <span className={sectionStyles.cardTitle}>{label}</span>

        <span className={`${styles.badge} ${isConfigured ? styles.badgeConfigured : ''}`}>
          {isConfigured ? 'Configured' : 'Not configured'}
        </span>

        <span className={`${styles.badge} ${isEnabled ? styles.badgeEnabled : ''}`}>
          {isEnabled ? <CheckCircle size={13} /> : <XCircle size={13} />}
          {isEnabled ? 'Enabled' : 'Disabled'}
        </span>

        {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
      </button>

      <button
        type="button"
        className={styles.deleteButton}
        onClick={onDelete}
        disabled={isSaving}
        aria-label={`Remove ${label}`}
      >
        <Trash2 size={16} />
      </button>
      </div>

      {isExpanded && (
        <div className={styles.body}>
          <p className={styles.description}>{description}</p>
          <ConfigForm

            key={`${config?.url || defaultUrl}|${isEnabled}|${config?.configured ?? false}|${config?.token_hint ?? ''}`}
            title={label}
            serviceName={serviceName}
            serviceType="PROVIDER"
            hideHeader
            hideToken={!requiresApiKey}
            showUrl={urlMode !== 'none'}
            readOnlyUrl={urlMode === 'fixed'}
            getKeyUrl={requiresApiKey ? getKeyUrl : undefined}
            initialUrl={config?.url || defaultUrl}
            hasStoredToken={!!config?.configured}
            storedTokenHint={config?.token_hint ?? null}

            initialEnabled={isEnabled}
            onSave={onSave}
            onValidate={onValidate}
            isSaving={isSaving}
          />
        </div>
      )}
    </div>
  );
}
