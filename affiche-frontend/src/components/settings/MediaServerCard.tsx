import { useState } from 'react';
import {
  CheckCircle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Save,
  Trash2,
  XCircle,
} from 'lucide-react';

import type { Library, LibrarySettings, MediaServerResponse } from '../../types';
import { MediaServerIcon, OverflowMenu } from '../common';
import { LanguageOrderPanel } from './LanguageOrderPanel';
import { LibraryRow } from './LibraryRow';
import { PosterFallbackPanel } from './PosterFallbackPanel';
import { ServerTokenPanel } from './ServerTokenPanel';
import { WebhookPanel } from './WebhookPanel';
import { SERVER_CONFIG } from './mediaServerHelpers';
import { toggleId, type LibraryWithSettings } from './mediaServerState';
import sectionStyles from './SettingsSection.module.css';
import styles from './MediaServerCard.module.css';

type CardSection = 'server' | 'libraries';

interface MediaServerCardProps {
  server: MediaServerResponse;
  libraries: LibraryWithSettings[];

  dirtyLibraries: Set<number>;

  isDirty: boolean;

  isExpanded: boolean;
  isSaving: boolean;
  isWebhookBusy: boolean;
  isTokenBusy: boolean;
  onToggleExpanded: () => void;
  onSettingChange: (libraryId: number, patch: Partial<LibrarySettings>) => void;
  onLanguageOrderChange: (order: string[]) => void;
  onPosterFallbackChange: (patch: Partial<MediaServerResponse>) => void;
  onSave: () => void;
  onUpdateToken: (token: string) => Promise<boolean>;
  onDeleteServer: () => void;
  onDeleteLibrary: (library: Library) => void;
  onAddLibraries: () => void;
  onToggleWebhook: (enabled: boolean) => void;
  onCopyWebhook: (url: string) => void;
  onTestWebhook: () => void;
  onRegenerateWebhook: () => void;
}

export function MediaServerCard({
  server,
  libraries,
  dirtyLibraries,
  isDirty,
  isExpanded,
  isSaving,
  isWebhookBusy,
  isTokenBusy,
  onToggleExpanded,
  onSettingChange,
  onLanguageOrderChange,
  onPosterFallbackChange,
  onSave,
  onUpdateToken,
  onDeleteServer,
  onDeleteLibrary,
  onAddLibraries,
  onToggleWebhook,
  onCopyWebhook,
  onTestWebhook,
  onRegenerateWebhook,
}: MediaServerCardProps) {

  const [expandedLibraries, setExpandedLibraries] = useState<Set<number>>(new Set());
  const [section, setSection] = useState<CardSection>('server');

  const hasDirtyLibrary = libraries.some((l) => dirtyLibraries.has(l.library.id));
  const hasUnsavedChanges = isDirty || hasDirtyLibrary;

  return (
    <div className={sectionStyles.card}>
      <button
        className={`${sectionStyles.cardHeader} ${styles.header}`}
        onClick={onToggleExpanded}
      >
        <span className={styles.icon}><MediaServerIcon type={server.type} size={18} /></span>
        <span className={sectionStyles.cardTitle}>{server.name}</span>
        {}
        <span
          className={styles.type}
          style={{ color: SERVER_CONFIG[server.type]?.color || 'var(--text-muted)' }}
        >
          {server.type}
        </span>
        <span className={sectionStyles.cardCount}>{libraries.length} libraries</span>
        {server.enabled ? (
          <CheckCircle size={16} className={styles.enabledIcon} />
        ) : (
          <XCircle size={16} className={styles.disabledIcon} />
        )}
        {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
      </button>

      {isExpanded && (
        <div className={`${sectionStyles.cardBody} ${styles.body}`}>
          {hasUnsavedChanges && (
            <div className={styles.saveRow}>
              <button
                className={`${sectionStyles.saveButton} ${styles.saveButtonSmall}`}
                onClick={onSave}
                disabled={isSaving}
              >
                <Save size={14} />
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}

          {

}
          <div className={styles.sectionSwitch} role="group" aria-label={`${server.name} sections`}>
            <button
              type="button"
              className={`${styles.sectionTab} ${section === 'server' ? styles.sectionTabActive : ''}`}
              aria-pressed={section === 'server'}
              onClick={() => setSection('server')}
            >
              Server settings
              {isDirty && <span className={styles.tabDot} aria-hidden="true" />}
            </button>
            <button
              type="button"
              className={`${styles.sectionTab} ${section === 'libraries' ? styles.sectionTabActive : ''}`}
              aria-pressed={section === 'libraries'}
              onClick={() => setSection('libraries')}
            >
              Libraries
              <span className={styles.tabCount}>{libraries.length}</span>
              {hasDirtyLibrary && <span className={styles.tabDot} aria-hidden="true" />}
            </button>
          </div>

          {section === 'libraries' ? (
            <>
              {libraries.length === 0 ? (
                <div className={`${sectionStyles.emptyState} ${styles.spacedEmptyState}`}>
                  No libraries synced. Sync the server to see libraries.
                </div>
              ) : (
                <div className={styles.libraryStack}>
                  {libraries.map(({ library, settings }) => (
                    <LibraryRow
                      key={library.id}
                      library={library}
                      settings={settings}
                      serverType={server.type}
                      serverWebhookEnabled={server.webhook_enabled}
                      isExpanded={expandedLibraries.has(library.id)}
                      isDirty={dirtyLibraries.has(library.id)}
                      isSaving={isSaving}
                      onToggleExpanded={() =>
                        setExpandedLibraries((prev) => toggleId(prev, library.id))
                      }
                      onChange={(patch) => onSettingChange(library.id, patch)}
                      onDelete={() => onDeleteLibrary(library)}
                    />
                  ))}
                </div>
              )}

              <div className={`${sectionStyles.divider} ${styles.footerEnd}`}>
                <button
                  className={`${sectionStyles.outlineButton} ${sectionStyles.outlineButtonAccent}`}
                  onClick={onAddLibraries}
                >
                  <RefreshCw size={14} />
                  Add Libraries
                </button>
              </div>
            </>
          ) : (
            <>
              <LanguageOrderPanel
                languageOrder={server.language_order}
                isSaving={isSaving}
                onChange={onLanguageOrderChange}
              />

              <PosterFallbackPanel
                fallbackToServerPoster={server.fallback_to_server_poster}
                skipStyleWhenNotTextless={server.skip_style_when_not_textless}
                isSaving={isSaving}
                onChange={onPosterFallbackChange}
              />

              <ServerTokenPanel
                serverType={server.type}
                serverUrl={server.url}
                isBusy={isTokenBusy}
                onSubmit={onUpdateToken}
              />

              <WebhookPanel
                serverType={server.type}
                enabled={server.webhook_enabled}
                token={server.webhook_token}
                isBusy={isWebhookBusy}
                onToggle={onToggleWebhook}
                onCopy={onCopyWebhook}
                onTest={onTestWebhook}
                onRegenerate={onRegenerateWebhook}
              />

              <div className={`${sectionStyles.divider} ${sectionStyles.dividerRow}`}>
                {
}
                <OverflowMenu
                  title="More actions"
                  placement="top-start"
                  triggerClassName={sectionStyles.menuTrigger}
                  items={[
                    { icon: <Trash2 size={16} />, label: 'Delete Server', onClick: onDeleteServer,
                      danger: true },
                  ]}
                />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
