import { useState } from 'react';
import { Plus } from 'lucide-react';

import { ConfirmModal } from '../common';
import { useMediaServers } from '../../hooks';
import { useToast } from '../../context/ToastContext';
import type {
  Library, MediaServerLibrary, MediaServerResponse, NewLibraryDefaults,
} from '../../types';
import { AddMediaServerPanel } from './AddMediaServerPanel';
import { AddLibrariesModal } from './AddLibrariesModal';
import { MediaServerCard } from './MediaServerCard';
import sectionStyles from './SettingsSection.module.css';
import styles from './MediaServersSettings.module.css';

interface MediaServersSettingsProps {
  onServerCreated?: () => void;
}

type DeleteTarget =
  | { type: 'server'; serverId: number; name: string }
  | { type: 'library'; serverId: number; libraryId: number; name: string };

const DELETE_MESSAGE: Record<DeleteTarget['type'], (name: string) => string> = {
  server: (name) =>
    `Delete "${name}"? This removes the server, its libraries and their tracked items from Affiche's own database only. Nothing is deleted on the media server itself — no media, metadata or artwork.`,
  library: (name) =>
    `Delete "${name}"? This removes the library and its tracked items from Affiche's own database only. Nothing is deleted on the media server itself — no media, metadata or artwork.`,
};

export function MediaServersSettings({ onServerCreated }: MediaServersSettingsProps) {
  const toast = useToast();
  const media = useMediaServers({ onServersChanged: onServerCreated });

  const [expandedServer, setExpandedServer] = useState<number | null | undefined>(undefined);
  const [isAddServerOpen, setIsAddServerOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [addLibrariesTo, setAddLibrariesTo] = useState<MediaServerResponse | null>(null);

  const openServer =
    expandedServer === undefined ? (media.servers[0]?.server.id ?? null) : expandedServer;

  const handleCopyWebhook = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success('Webhook URL copied');
    } catch {
      toast.error('Could not copy to clipboard');
    }
  };

  const handleOpenAddLibraries = (server: MediaServerResponse) => {
    setAddLibrariesTo(server);
    media.loadAvailableLibraries(server.id);
  };

  const handleAddLibraries = async (libraries: MediaServerLibrary[],
                                   defaults: NewLibraryDefaults) => {
    if (!addLibrariesTo) return;
    if (await media.addLibraries(addLibrariesTo.id, libraries, defaults)) {
      setAddLibrariesTo(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    const deleted =
      deleteTarget.type === 'server'
        ? await media.deleteServer(deleteTarget.serverId)
        : await media.deleteLibrary(deleteTarget.serverId, deleteTarget.libraryId);
    if (deleted) setDeleteTarget(null);
  };

  return (
    <section className={sectionStyles.section}>
      <div className={sectionStyles.sectionHeader}>
        <div>
          <h2 className={sectionStyles.sectionTitle}>Media Servers</h2>
          <p className={sectionStyles.sectionDescription}>
            Connect your media servers and configure library settings.
          </p>
        </div>
        <button className={sectionStyles.saveButton} onClick={() => setIsAddServerOpen(true)}>
          <Plus size={16} />
          Add Media Server
        </button>
      </div>

      {media.servers.length > 0 ? (
        <div className={styles.group}>
          <h3 className={styles.groupTitle}>Connected Servers</h3>
          <div className={sectionStyles.cardList}>
            {media.servers.map(({ server, libraries }) => (
              <MediaServerCard
                key={server.id}
                server={server}
                libraries={libraries}
                dirtyLibraries={media.dirtyLibraries}
                isDirty={media.dirtyServers.has(server.id)}
                isExpanded={openServer === server.id}
                isSaving={media.isSaving}
                isWebhookBusy={media.webhookBusy === server.id}
                isTokenBusy={media.tokenBusy === server.id}
                onToggleExpanded={() =>
                  setExpandedServer(openServer === server.id ? null : server.id)
                }
                onSettingChange={(libraryId, patch) =>
                  media.changeLibrarySettings(server.id, libraryId, patch)
                }
                onLanguageOrderChange={(order) => media.changeLanguageOrder(server.id, order)}
                onPosterFallbackChange={(patch) => media.changePosterFallback(server.id, patch)}
                onSave={() => media.saveServer(server.id)}
                onUpdateToken={(token) => media.updateToken(server.id, token)}
                onDeleteServer={() =>
                  setDeleteTarget({ type: 'server', serverId: server.id, name: server.name })
                }
                onDeleteLibrary={(library: Library) =>
                  setDeleteTarget({
                    type: 'library',
                    serverId: server.id,
                    libraryId: library.id,
                    name: library.name,
                  })
                }
                onAddLibraries={() => handleOpenAddLibraries(server)}
                onToggleWebhook={(enabled) => media.toggleWebhook(server.id, enabled)}
                onCopyWebhook={handleCopyWebhook}
                onTestWebhook={() => media.testWebhook(server.id)}
                onRegenerateWebhook={() => media.regenerateWebhook(server.id)}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className={`${sectionStyles.emptyState} ${styles.group}`}>
          No media servers connected yet. Click "Add Media Server" to connect your Plex or Jellyfin
          server.
        </div>
      )}

      {isAddServerOpen && (
        <AddMediaServerPanel
          onClose={() => setIsAddServerOpen(false)}
          onCreated={async () => {
            await media.serverCreated();
            setIsAddServerOpen(false);
          }}
        />
      )}

      {deleteTarget && (
        <ConfirmModal
          title={`Delete ${deleteTarget.type === 'server' ? 'Server' : 'Library'}`}
          message={DELETE_MESSAGE[deleteTarget.type](deleteTarget.name)}
          confirmLabel={media.isDeleting ? 'Deleting...' : 'Delete'}
          variant="danger"
          isBusy={media.isDeleting}
          onConfirm={handleConfirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      {addLibrariesTo && (
        <AddLibrariesModal

          key={addLibrariesTo.id}
          serverName={addLibrariesTo.name}
          libraries={media.availableLibraries}
          isLoading={media.isLoadingAvailable}
          isAdding={media.isAddingLibraries}
          onClose={() => setAddLibrariesTo(null)}
          onAdd={handleAddLibraries}
        />
      )}
    </section>
  );
}
