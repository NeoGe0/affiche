import { useId, useState } from 'react';
import { ArrowLeft, Save } from 'lucide-react';
import { Modal } from '../common';
import { ConfigForm } from './ConfigForm';
import { configApi, errorMessage, serviceApi } from '../../api';
import { useToast } from '../../context/ToastContext';
import {
  POSTER_PROVIDER_CARDS,
  providerLabel,
  providerRequiresApiKey,
  providerUrlMode,
  type PosterProvider,
} from '../../constants/providers';
import { PROVIDER_ICONS } from './providerIcons';
import sectionStyles from './SettingsSection.module.css';
import panelStyles from './AddMediaServerPanel.module.css';
import styles from './AddProviderPanel.module.css';

interface AddProviderPanelProps {

  existing: PosterProvider[];
  onClose: () => void;
  onAdded: () => void;
}

export function AddProviderPanel({ existing, onClose, onAdded }: AddProviderPanelProps) {
  const [selected, setSelected] = useState<PosterProvider | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [canSave, setCanSave] = useState(false);
  const toast = useToast();
  const formId = useId();

  const available = POSTER_PROVIDER_CARDS.filter((p) => !existing.includes(p.serviceName));
  const meta = selected ? POSTER_PROVIDER_CARDS.find((p) => p.serviceName === selected) : null;

  const handleSave = async (data: { url: string; token?: string; enabled: boolean }) => {
    if (!selected) return;
    setIsSaving(true);
    try {
      await configApi.createConfig({
        name: selected,
        type: 'PROVIDER',
        url: data.url,
        token: data.token,
        enabled: data.enabled,
      });
      toast.success(`${providerLabel(selected)} added`);
      onAdded();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to add the provider'), {
        title: providerLabel(selected),
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      size="drawer"
      label="Add poster provider"
      isBusy={isSaving}
      onClose={onClose}

      footer={meta ? (
        <>
          <button
            type="button"
            className={sectionStyles.outlineButton}
            onClick={onClose}
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            type="submit"
            form={formId}
            className={sectionStyles.saveButton}
            disabled={isSaving || !canSave}
            title={!canSave ? 'Validate the credentials first' : undefined}
          >
            <Save size={16} />
            {isSaving ? 'Saving...' : 'Add Provider'}
          </button>
        </>
      ) : undefined}
    >
      <div className={panelStyles.header}>
        {meta ? (
          <button
            type="button"
            className={styles.backButton}
            onClick={() => setSelected(null)}
            disabled={isSaving}
          >
            <ArrowLeft size={14} /> All providers
          </button>
        ) : null}
        <h3 className={styles.title}>{meta ? providerLabel(meta.serviceName) : 'Add Provider'}</h3>
        <p className={styles.description}>
          {meta ? meta.description : 'Pick a poster artwork provider to configure'}
        </p>
      </div>

      <div className={panelStyles.content}>
        {meta ? (
          <ConfigForm
            title={providerLabel(meta.serviceName)}
            serviceName={meta.serviceName}
            serviceType="PROVIDER"
            hideHeader
            hideToken={!providerRequiresApiKey(meta.serviceName)}
            showUrl={providerUrlMode(meta.serviceName) !== 'none'}
            readOnlyUrl={providerUrlMode(meta.serviceName) === 'fixed'}
            getKeyUrl={providerRequiresApiKey(meta.serviceName) ? meta.getKeyUrl : undefined}
            initialUrl={meta.defaultUrl}
            initialEnabled
            formId={formId}
            onSubmittableChange={setCanSave}
            onSave={handleSave}
            onValidate={(url, token) =>
              serviceApi
                .testProvider(meta.serviceName, token, url)
                .then(() => true)
                .catch(() => false)
            }
            isSaving={isSaving}
          />
        ) : available.length === 0 ? (
          <p className={styles.allAdded}>Every available provider is already configured.</p>
        ) : (
          <ul className={styles.choices}>
            {available.map((provider) => (
              <li key={provider.serviceName}>
                <button
                  type="button"
                  className={styles.choice}
                  onClick={() => setSelected(provider.serviceName)}
                >
                  <span className={styles.choiceIcon} style={{ color: provider.accentColor }}>
                    {PROVIDER_ICONS[provider.serviceName]}
                  </span>
                  <span className={styles.choiceText}>
                    <span className={styles.choiceName}>{providerLabel(provider.serviceName)}</span>
                    <span className={styles.choiceDescription}>{provider.description}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
