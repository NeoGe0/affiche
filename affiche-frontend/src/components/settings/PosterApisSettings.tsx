import { useState } from 'react';
import { Plus } from 'lucide-react';
import { PosterProviderCard } from './PosterProviderCard';
import { AddProviderPanel } from './AddProviderPanel';
import { PROVIDER_ICONS } from './providerIcons';
import { ConfirmModal } from '../common';
import { configApi, errorMessage, serviceApi } from '../../api';
import { useToast } from '../../context/ToastContext';
import type { ServiceConfiguration } from '../../types';
import {
  POSTER_PROVIDER_CARDS,
  providerLabel,
  type PosterProvider,
} from '../../constants/providers';
import styles from './SettingsSection.module.css';

interface PosterApisSettingsProps {
  configs: Partial<Record<PosterProvider, ServiceConfiguration>>;
  onConfigSaved: () => void;
}

export function PosterApisSettings({ configs, onConfigSaved }: PosterApisSettingsProps) {
  const [savingProvider, setSavingProvider] = useState<string | null>(null);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<PosterProvider | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const toast = useToast();

  const added = POSTER_PROVIDER_CARDS.filter((provider) => configs[provider.serviceName]);

  const handleSaveProvider = async (
    serviceName: string,
    data: { url: string; token?: string; enabled: boolean }
  ) => {
    setSavingProvider(serviceName);
    try {
      await configApi.createConfig({
        name: serviceName,
        type: 'PROVIDER',
        url: data.url,
        token: data.token,
        enabled: data.enabled,
      });
      onConfigSaved();
      toast.success(`${providerLabel(serviceName)} saved`);
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to save the provider'), {
        title: providerLabel(serviceName),
      });
    } finally {
      setSavingProvider(null);
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setIsDeleting(true);
    try {
      await configApi.deleteConfig(pendingDelete);
      onConfigSaved();
      toast.success(`${providerLabel(pendingDelete)} removed`);
      setPendingDelete(null);
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to remove the provider'), {
        title: providerLabel(pendingDelete),
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const createValidateHandler = (provider: string) => {
    return async (url: string, token: string): Promise<boolean> => {
      try {
        await serviceApi.testProvider(provider, token, url);
        return true;
      } catch {
        return false;
      }
    };
  };

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Poster APIs</h2>
          <p className={styles.sectionDescription}>
            Add the poster artwork providers you want Affiche to search. At least one enabled
            provider is needed to fetch posters.
          </p>
        </div>
        <button className={styles.saveButton} onClick={() => setIsAddOpen(true)}>
          <Plus size={16} />
          Add Provider
        </button>
      </div>

      {added.length > 0 ? (
        <div className={styles.cardList}>
          {added.map((provider) => (
            <PosterProviderCard
              key={provider.serviceName}
              label={providerLabel(provider.serviceName)}
              description={provider.description}
              icon={PROVIDER_ICONS[provider.serviceName]}
              accentColor={provider.accentColor}
              getKeyUrl={provider.getKeyUrl}
              config={configs[provider.serviceName] ?? null}
              serviceName={provider.serviceName}
              defaultUrl={provider.defaultUrl}
              isSaving={savingProvider === provider.serviceName}
              onSave={(data) => handleSaveProvider(provider.serviceName, data)}
              onDelete={() => setPendingDelete(provider.serviceName)}
              onValidate={createValidateHandler(provider.serviceName)}
            />
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          No poster providers yet. Click "Add Provider" to configure one — TMDB is a good place to
          start.
        </div>
      )}

      {isAddOpen && (
        <AddProviderPanel
          existing={added.map((provider) => provider.serviceName)}
          onClose={() => setIsAddOpen(false)}
          onAdded={onConfigSaved}
        />
      )}

      {pendingDelete && (
        <ConfirmModal
          title={`Remove ${providerLabel(pendingDelete)}?`}
          message="Its API key is stored encrypted and cannot be recovered — you will have to enter it again to add this provider back."
          confirmLabel="Remove"
          variant="danger"
          isBusy={isDeleting}
          onConfirm={handleDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </section>
  );
}
