import { useState } from 'react';
import { ChevronDown, ChevronRight, Palette, Trash2 } from 'lucide-react';

import { LibraryTypeIcon, ProviderOrderList } from '../common';
import { reconcileProviderOrder } from '../common/providerOrder';
import { useProviderStatus } from '../../hooks';
import { MEDIA_SERVER_BRAND } from '../../constants/mediaServers';
import type {
  AutoPickupAction,
  Library,
  LibrarySettings,
  MediaServerType,
} from '../../types';
import { hasCustomStyle } from './libraryStyle';
import { LibraryStyleModal } from './LibraryStyleModal';
import { decomposeInterval, intervalToMinutes, type IntervalUnit } from './mediaServerState';
import sectionStyles from './SettingsSection.module.css';
import styles from './LibraryRow.module.css';

interface LibraryRowProps {
  library: Library;
  settings: LibrarySettings;

  serverType: MediaServerType;

  serverWebhookEnabled: boolean;
  isExpanded: boolean;
  isDirty: boolean;

  isSaving: boolean;
  onToggleExpanded: () => void;
  onChange: (patch: Partial<LibrarySettings>) => void;
  onDelete: () => void;
}

export function LibraryRow({
  library,
  settings,
  serverType,
  serverWebhookEnabled,
  isExpanded,
  isDirty,
  isSaving,
  onToggleExpanded,
  onChange,
  onDelete,
}: LibraryRowProps) {
  const { addedProviders } = useProviderStatus();
  const [isEditingStyle, setIsEditingStyle] = useState(false);
  const { value: intervalValue, unit: intervalUnit } = decomposeInterval(
    settings.auto_sync_interval_minutes
  );
  const isCustomStyle = hasCustomStyle(settings);

  return (
    <div className={`${styles.row} ${isDirty ? styles.rowDirty : ''}`}>
      <button className={styles.toggle} onClick={onToggleExpanded}>
        <span className={styles.icon}><LibraryTypeIcon type={library.library_type} /></span>
        <span className={styles.name}>{library.name}</span>
        {isDirty && <span className={styles.dirtyBadge}>Unsaved</span>}
        <span className={styles.count}>{library.media_count} items</span>
        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>

      {isExpanded && (
        <div className={styles.body}>
          <div className={sectionStyles.settingsGroup}>
            <label className={sectionStyles.toggle}>
              <input
                type="checkbox"
                checked={settings.enabled}
                onChange={(e) => onChange({ enabled: e.target.checked })}
              />
              <span>Enabled</span>
            </label>
            <p className={sectionStyles.settingDescription}>
              Include this library in poster processing
            </p>
          </div>

          <div className={sectionStyles.settingsGroup}>
            <label className={sectionStyles.toggle}>
              <input
                type="checkbox"
                checked={settings.upload_enabled}
                onChange={(e) => onChange({ upload_enabled: e.target.checked })}
              />
              <span>Upload to {MEDIA_SERVER_BRAND[serverType].name}</span>
            </label>
            <p className={sectionStyles.settingDescription}>
              Upload generated posters to the server
            </p>
          </div>

          {library.library_type === 'show' && (
            <div className={sectionStyles.settingsGroup}>
              <label className={sectionStyles.toggle}>
                <input
                  type="checkbox"
                  checked={settings.track_episodes}
                  onChange={(e) => onChange({ track_episodes: e.target.checked })}
                />
                <span>Track episodes</span>
              </label>
              <p className={sectionStyles.settingDescription}>
                Sync per-episode info (resolution, codec, size) so you can browse episodes.
                Increases sync time — re-sync the library after enabling.
              </p>
            </div>
          )}

          <div className={sectionStyles.settingsGroup}>
            <label className={sectionStyles.toggle}>
              <input
                type="checkbox"
                checked={settings.track_collections}
                onChange={(e) => onChange({ track_collections: e.target.checked })}
              />
              <span>Track collections</span>
            </label>
            <p className={sectionStyles.settingDescription}>
              Sync this library's collections and which items are in them, so you can browse and
              edit them. Costs one extra call per collection — re-sync the library after enabling.
            </p>
          </div>

          <div className={sectionStyles.settingsGroup}>
            <label className={sectionStyles.toggle}>
              <input
                type="checkbox"
                checked={settings.auto_sync_enabled}
                onChange={(e) => onChange({ auto_sync_enabled: e.target.checked })}
              />
              <span>Scheduled auto-sync</span>
            </label>
            <p className={sectionStyles.settingDescription}>
              Periodically re-sync to pick up newly-added items
              {serverWebhookEnabled ? ' (webhooks also enabled on this server)' : ''}.
            </p>

            {settings.auto_sync_enabled && (
              <div className={styles.intervalRow}>
                <span className={styles.intervalLabel}>Check every</span>
                {
}
                <input
                  type="number"
                  min={1}
                  aria-label="Check every"
                  value={intervalValue}
                  onChange={(e) =>
                    onChange({
                      auto_sync_interval_minutes: intervalToMinutes(
                        Number(e.target.value) || 1,
                        intervalUnit
                      ),
                    })
                  }
                  className={`${styles.smallInput} ${styles.intervalNumber}`}
                />
                <select
                  value={intervalUnit}
                  aria-label="Interval unit"
                  onChange={(e) =>
                    onChange({
                      auto_sync_interval_minutes: intervalToMinutes(
                        intervalValue,
                        e.target.value as IntervalUnit
                      ),
                    })
                  }
                  className={styles.smallInput}
                >
                  <option value="hours">{intervalValue === 1 ? 'hour' : 'hours'}</option>
                  <option value="days">{intervalValue === 1 ? 'day' : 'days'}</option>
                </select>
              </div>
            )}

            <label className={styles.field}>
              <span className={styles.fieldLabel}>When a new item is found</span>
              <select
                value={settings.auto_pickup_action}
                onChange={(e) =>
                  onChange({ auto_pickup_action: e.target.value as AutoPickupAction })
                }
                className={styles.actionSelect}
              >
                <option value="sync">Sync only (mark unprocessed)</option>
                <option value="generate">Generate posters (no upload)</option>
                <option value="upload">Generate + upload posters</option>
              </select>
              <span className={`${sectionStyles.settingDescription} ${styles.fieldHint}`}>
                Applies to both scheduled and webhook pickup.
              </span>
            </label>
          </div>

          <div className={sectionStyles.settingsGroup}>
            <h4 className={sectionStyles.settingsLabel}>Provider Priority</h4>
            <p className={sectionStyles.settingDescription}>
              Drag to reorder. First provider with a result will be used.
            </p>
            <ProviderOrderList
              providers={reconcileProviderOrder(settings.provider_order, addedProviders)}
              onChange={(provider_order) => onChange({ provider_order })}
              disabled={isSaving}
            />
          </div>

          <div className={sectionStyles.settingsGroup}>
            <h4 className={sectionStyles.settingsLabel}>Poster Style</h4>
            <p className={sectionStyles.settingDescription}>
              {isCustomStyle
                ? 'This library overrides the global style options.'
                : 'Following the global style options.'}
            </p>
            <button className={sectionStyles.outlineButton} onClick={() => setIsEditingStyle(true)}>
              <Palette size={14} />
              {isCustomStyle ? 'Edit custom style' : 'Set a custom style'}
            </button>
          </div>

          <div className={sectionStyles.divider}>
            <button
              className={`${sectionStyles.outlineButton} ${sectionStyles.outlineButtonDanger}`}
              onClick={onDelete}
            >
              <Trash2 size={14} />
              Delete Library
            </button>
          </div>

          {isEditingStyle && (
            <LibraryStyleModal
              libraryName={library.name}
              mediaServerId={library.media_server_id}
              libraryId={library.id}
              settings={settings}
              onApply={onChange}
              onClose={() => setIsEditingStyle(false)}
            />
          )}
        </div>
      )}
    </div>
  );
}
