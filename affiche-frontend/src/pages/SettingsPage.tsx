import { useCallback, useEffect, useEffectEvent, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { MediaServersSettings, PosterApisSettings, StyleSettings, GeneralSettings, AppearanceSettings, UsersSettings, NotificationsSettings } from '../components/settings';
import { configApi, errorMessage } from '../api';
import { useProviderStatus } from '../hooks';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import type { PosterProvider } from '../constants/providers';
import type { ServiceConfiguration } from '../types';
import styles from './SettingsPage.module.css';

type SettingsTab = 'media-servers' | 'apis' | 'style' | 'notifications' | 'general' | 'users';

const VALID_TABS: SettingsTab[] = ['media-servers', 'apis', 'style', 'notifications', 'general', 'users'];

const ADMIN_TABS: SettingsTab[] = ['media-servers', 'apis', 'style', 'notifications', 'general'];

const USERS_URL = '/settings?tab=users';

interface SettingsPageProps {
  onDataChanged?: () => void;
}

export function SettingsPage({ onDataChanged }: SettingsPageProps) {
  const [searchParams] = useSearchParams();
  const { isAdmin } = useAuth();
  const tabParam = searchParams.get('tab') as SettingsTab | null;
  const activeTab: SettingsTab =
    tabParam && VALID_TABS.includes(tabParam) ? tabParam : 'media-servers';

  const [configs, setConfigs] = useState<Partial<Record<PosterProvider, ServiceConfiguration>>>({});
  const [isLoading, setIsLoading] = useState(true);
  const { reload: reloadProviderStatus } = useProviderStatus();
  const toast = useToast();

  const loadConfigs = useCallback(async () => {

    if (!isAdmin) {
      setIsLoading(false);
      return;
    }
    try {
      const configs = await configApi.findConfigs('PROVIDER');
      const loaded: Partial<Record<PosterProvider, ServiceConfiguration>> = {};
      configs.forEach((config) => {
        loaded[config.name as PosterProvider] = config;
      });
      setConfigs(loaded);
    } catch (error) {

      toast.error(
        errorMessage(error, 'Could not load the saved poster providers. None are shown.'),
        { title: 'Poster APIs' }
      );
      setConfigs({});
    }

    reloadProviderStatus().catch(() => {});
    setIsLoading(false);
  }, [isAdmin, reloadProviderStatus, toast]);

  const loadOnMount = useEffectEvent(() => {
    loadConfigs();
  });

  useEffect(() => {
    loadOnMount();
  }, []);

  const reloadConfigs = useCallback(() => {
    setIsLoading(true);
    return loadConfigs();
  }, [loadConfigs]);

  if (!isAdmin && ADMIN_TABS.includes(activeTab)) {
    return <Navigate to={USERS_URL} replace />;
  }

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>Loading settings...</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        {activeTab === 'media-servers' && (
          <MediaServersSettings
            onServerCreated={onDataChanged}
          />
        )}

        {activeTab === 'apis' && (
          <PosterApisSettings configs={configs} onConfigSaved={reloadConfigs} />
        )}

        {activeTab === 'style' && <StyleSettings />}

        {activeTab === 'notifications' && <NotificationsSettings />}

        {activeTab === 'users' && <UsersSettings />}

        {
}
        {activeTab === 'general' && (
          <>
            <AppearanceSettings />
            <GeneralSettings />
          </>
        )}
      </div>
    </div>
  );
}
