import { useEffect, useEffectEvent, useState } from 'react';
import { CheckCircle, Loader } from 'lucide-react';
import { LibraryTypeIcon, Modal, ProviderOrderList } from '../common';
import { reconcileProviderOrder } from '../common/providerOrder';
import { settingsApi } from '../../api';
import { useProviderStatus } from '../../hooks';
import type { MediaServerLibrary, NewLibraryDefaults } from '../../types';
import sectionStyles from './SettingsSection.module.css';
import styles from './AddLibrariesModal.module.css';

interface AddLibrariesModalProps {
  serverName: string;

  libraries: MediaServerLibrary[];
  isLoading: boolean;
  isAdding: boolean;
  onClose: () => void;
  onAdd: (libraries: MediaServerLibrary[], defaults: NewLibraryDefaults) => void;
}

export function AddLibrariesModal({
  serverName,
  libraries,
  isLoading,
  isAdding,
  onClose,
  onAdd,
}: AddLibrariesModalProps) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set(libraries.map((l) => l.id)));
  const { addedProviders } = useProviderStatus();

  const [defaults, setDefaults] = useState<Required<NewLibraryDefaults> | null>(null);

  const loadDefaults = useEffectEvent(async () => {
    try {
      const settings = await settingsApi.getSettings();
      setDefaults({
        new_library_enabled: settings.new_library_enabled,
        new_library_upload_enabled: settings.new_library_upload_enabled,
        new_library_provider_order: reconcileProviderOrder(
          settings.new_library_provider_order, addedProviders),
      });
    } catch {

      setDefaults(null);
    }
  });

  useEffect(() => {
    void loadDefaults();
  }, []);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const update = (changes: NewLibraryDefaults) =>
    setDefaults((prev) => (prev ? { ...prev, ...changes } : prev));

  const hasLibraries = libraries.length > 0;

  return (
    <Modal
      size="wide"
      label="Add libraries"
      title="Add Libraries"
      description={
        <>
          Select libraries from <strong>{serverName}</strong> to add to Affiche.
        </>
      }
      isBusy={isAdding}
      onClose={onClose}
      footer={
        <>
          <button className={styles.cancelButton} onClick={onClose} disabled={isAdding}>
            Cancel
          </button>
          {hasLibraries && (
            <button
              className={styles.addButton}
              onClick={() => onAdd(libraries.filter((l) => selected.has(l.id)), defaults ?? {})}
              disabled={isAdding || selected.size === 0}
            >
              {isAdding ? <Loader size={14} className={styles.spinning} /> : <CheckCircle size={14} />}
              {isAdding ? 'Adding...' : `Add ${selected.size} Libraries`}
            </button>
          )}
        </>
      }
    >
      <div className={styles.content}>
        {isLoading ? (
          <div className={styles.loading}>
            <Loader size={20} className={styles.spinning} />
            <span>Loading libraries...</span>
          </div>
        ) : !hasLibraries ? (
          <div className={styles.empty}>
            All libraries from this server are already added to Affiche.
          </div>
        ) : (
          <>
            <div className={styles.selectionBar}>
              <span className={styles.count}>
                {selected.size} of {libraries.length} selected
              </span>
              <div className={styles.bulkActions}>
                <button
                  type="button"
                  className={styles.bulkButton}
                  onClick={() => setSelected(new Set(libraries.map((l) => l.id)))}
                >
                  Select All
                </button>
                <button
                  type="button"
                  className={`${styles.bulkButton} ${styles.bulkButtonMuted}`}
                  onClick={() => setSelected(new Set())}
                >
                  Select None
                </button>
              </div>
            </div>

            <div className={styles.list}>
              {libraries.map((library) => (
                <label
                  key={library.id}
                  className={`${styles.option} ${selected.has(library.id) ? styles.optionSelected : ''}`}
                >
                  <input
                    type="checkbox"
                    className={styles.checkbox}
                    checked={selected.has(library.id)}
                    onChange={() => toggle(library.id)}
                  />
                  <span className={styles.icon}><LibraryTypeIcon type={library.type} /></span>
                  <span className={styles.name}>{library.name}</span>
                  <span className={styles.meta}>{library.item_count} items</span>
                  <span className={`${styles.meta} ${styles.type}`}>{library.type}</span>
                </label>
              ))}
            </div>

            {defaults && (
              <div className={styles.defaults}>
                <h4 className={sectionStyles.groupTitle}>What they start out as</h4>
                <p className={sectionStyles.groupDescription}>
                  Applied to the libraries added now. Each one can be changed afterwards in its own
                  row.
                </p>

                <div className={sectionStyles.row}>
                  <label className={sectionStyles.checkbox}>
                    <input
                      type="checkbox"
                      checked={defaults.new_library_enabled}
                      onChange={(e) => update({ new_library_enabled: e.target.checked })}
                    />
                    <span>Enabled for poster processing</span>
                  </label>
                </div>

                <div className={sectionStyles.row}>
                  <label className={sectionStyles.checkbox}>
                    <input
                      type="checkbox"
                      checked={defaults.new_library_upload_enabled}
                      onChange={(e) => update({ new_library_upload_enabled: e.target.checked })}
                    />
                    <span>Upload generated posters to the server</span>
                  </label>
                </div>

                <div className={styles.providerOrder}>
                  <span className={sectionStyles.label}>Provider priority</span>
                  <ProviderOrderList
                    providers={defaults.new_library_provider_order}
                    onChange={(new_library_provider_order) => update({ new_library_provider_order })}
                    disabled={isAdding}
                  />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
