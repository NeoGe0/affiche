import { useState } from 'react';
import { Layers, Plus, RefreshCw, Search, Sparkles } from 'lucide-react';

import { CollectionCard, CollectionDetail, ItemPickerModal, TitlePromptModal } from '../components/collections';
import { PosterBrowserModal, posterTargetFromCollection } from '../components/library';
import { ConfirmModal, OverflowMenu, TaskProgressBar } from '../components/common';
import { collectionsApi, errorMessage, libraryApi, postersApi } from '../api';
import { useToast } from '../context/ToastContext';
import { useCollections, useEventStream, useTaskTracking } from '../hooks';
import type { Collection, Library, LibraryItem, OverlayOptions, TextOptions } from '../types';
import styles from './CollectionsPage.module.css';

interface CollectionsPageProps {
  mediaServerId?: number;
  mediaServerName?: string;
  libraries: Library[];
  selectedLibraryId?: number;
}

export function CollectionsPage({
  mediaServerId,
  mediaServerName,
  libraries,
  selectedLibraryId,
}: CollectionsPageProps) {
  const [search, setSearch] = useState('');
  const [openId, setOpenId] = useState<number | null>(null);
  const [detailKey, setDetailKey] = useState(0);
  const [dialog, setDialog] = useState<Dialog | null>(null);

  const [posterFor, setPosterFor] = useState<Collection | null>(null);
  const [isSavingPoster, setIsSavingPoster] = useState(false);

  const [uploadDefault, setUploadDefault] = useState(false);
  const toast = useToast();

  const library = libraries.find((l) => l.id === selectedLibraryId);
  const collections = useCollections({ mediaServerId, libraryId: library?.id, search });

  const {
    isActionLoading, setIsActionLoading, taskMessage, taskProgress,
    startTaskTracking, attachRunningTask, handleTaskStatus, handleTaskProgress,
  } = useTaskTracking({ onTaskFinished: () => collections.reload() });

  useEventStream({
    onLibrarySynced: (_mediaServerId, libraryId) => {
      if (libraryId == null || libraryId === library?.id) collections.reload();
    },
    onTaskStatus: handleTaskStatus,
    onTaskProgress: handleTaskProgress,

    onConnected: attachRunningTask,
  });

  if (!mediaServerId || !library) {
    return (
      <div className={styles.page}>
        <div className={styles.empty}>
          <Layers size={32} />
          <h2>Pick a library</h2>
          <p>Collections belong to a library — choose one in the sidebar to see its collections.</p>
        </div>
      </div>
    );
  }

  const afterWrite = () => setDetailKey((key) => key + 1);

  const applyPoster = async (
    collection: Collection,
    posterUrl: string,
    opts: {
      overlayOptions?: OverlayOptions;
      textOptions?: TextOptions;
      jpegQuality?: number;
      title?: string;
      upload?: boolean;
    },
  ) => {
    if (!mediaServerId || !library) return;
    setIsSavingPoster(true);
    try {
      await postersApi.applyCollectionPoster({
        mediaServerId,
        libraryId: library.id,
        collectionId: collection.id,
        posterUrl,
        jpegQuality: opts.jpegQuality,
        title: opts.title,
        overlayOptions: opts.overlayOptions,
        textOptions: opts.textOptions,
        upload: opts.upload,
      });
      setPosterFor(null);
      afterWrite();
      collections.reload();
    } catch (error) {
      toast.error(errorMessage(error, 'Could not apply the poster to this collection.'),
        { title: 'Collection poster' });
    } finally {
      setIsSavingPoster(false);
    }
  };

  const matchCollections = async () => {
    setDialog(null);
    if (!mediaServerId || !library) return;
    setIsActionLoading(true);
    try {
      const response = await collectionsApi.resolveIds(mediaServerId, library.id);
      startTaskTracking(response.task_id, 'Matching collections…');
    } catch (error) {

      setIsActionLoading(false);
      toast.error(errorMessage(error, 'Could not start the collection matching.'),
        { title: 'Collections' });
    }
  };

  const openPosterPicker = async (collection: Collection) => {
    try {
      const settings = await libraryApi.getLibrarySettings(mediaServerId, library.id);
      setUploadDefault(settings.upload_enabled);
    } catch {
      setUploadDefault(false);
    }
    setPosterFor(collection);
  };

  const posterModal = posterFor && library && (
    <PosterBrowserModal
      target={posterTargetFromCollection(posterFor, library.library_type)}
      isSaving={isSavingPoster}
      defaultUpload={uploadDefault}
      onClose={() => setPosterFor(null)}
      onSave={(posterUrl, opts) => void applyPoster(posterFor, posterUrl, opts)}
    />
  );
  const close = () => setDialog(null);

  if (openId != null) {
    return (
      <>
        <CollectionDetail
          mediaServerId={mediaServerId}
          libraryId={library.id}
          collectionId={openId}
          refreshKey={detailKey}
          isBusy={collections.isBusy}
          onBack={() => setOpenId(null)}
          onRename={(title) => setDialog({ kind: 'rename', collectionId: openId, title })}
          onDelete={(title) => setDialog({ kind: 'delete', collectionId: openId, title })}
          onAddItems={(memberIds) => setDialog({ kind: 'add', collectionId: openId, memberIds })}
          onRemoveItem={(item) => setDialog({ kind: 'remove', collectionId: openId, item })}
          onToggleLock={async (locked) => {
            await collections.setLock(openId, locked);
            afterWrite();
          }}
          onSelectPoster={(collection) => void openPosterPicker(collection)}
        />
        {renderDialog()}
        {posterModal}
      </>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.breadcrumb}>{mediaServerName} / {library.name}</p>
          <h1 className={styles.title}>Collections</h1>
        </div>
        <div className={styles.controls}>
          <div className={styles.searchBox}>
            <Search size={16} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search collections…"
            />
          </div>
          {
}
          <button
            className={styles.secondary}
            onClick={() => setDialog({ kind: 'match' })}
            disabled={isActionLoading}
            title="Look these collections up in the poster catalogue"
          >
            <Sparkles size={16} /> Match collections
          </button>
          <button className={styles.primary} onClick={() => setDialog({ kind: 'create' })}>
            <Plus size={16} /> New collection
          </button>
          <OverflowMenu
            triggerClassName={styles.secondary}
            items={[
              { icon: <RefreshCw size={16} />, label: 'Refresh', onClick: collections.reload },
            ]}
          />
        </div>
        {isActionLoading && taskMessage && (
          <p className={styles.taskStatus}>{taskMessage}</p>
        )}
        {isActionLoading && <TaskProgressBar progress={taskProgress} />}
      </header>

      {collections.isLoading ? (
        <p className={styles.message}>Loading…</p>
      ) : collections.collections.length === 0 ? (
        <div className={styles.empty}>
          <Layers size={32} />
          <h2>No collections</h2>
          <p>
            {search
              ? 'No collection matches that search.'
              : `Collection sync is off by default. Turn on "Track collections" for ${library.name} in
                 Settings → Media Servers, then sync the library — or create one here.`}
          </p>
        </div>
      ) : (
        <div className={styles.grid}>
          {collections.collections.map((collection) => (
            <CollectionCard
              key={collection.id}
              collection={collection}
              onClick={() => { setOpenId(collection.id); setDetailKey((k) => k + 1); }}
            />
          ))}
        </div>
      )}

      {renderDialog()}
    </div>
  );

  function renderDialog() {
    if (!dialog || !mediaServerId || !library) return null;

    if (dialog.kind === 'match') {
      return (
        <ConfirmModal
          title="Match Collections"
          message={`This will look up the collections in ${library.name} that have no catalogue match yet, so their artwork can come from TMDB or MediUX. Collections that match nothing are re-checked every time you run this. Continue?`}
          confirmLabel="Match"
          onConfirm={() => void matchCollections()}
          onCancel={close}
        />
      );
    }

    if (dialog.kind === 'create') {
      return (
        <ItemPickerModal
          title="New collection"
          confirmLabel="Choose items"
          mediaServerId={mediaServerId}
          libraryId={library.id}
          isBusy={collections.isBusy}
          onClose={close}
          onConfirm={(itemIds) => setDialog({ kind: 'create-name', itemIds })}
        />
      );
    }

    if (dialog.kind === 'create-name') {
      return (
        <TitlePromptModal
          heading="Name the collection"
          confirmLabel="Create"
          isBusy={collections.isBusy}
          onClose={close}
          onConfirm={async (title) => {
            const created = await collections.create(title, dialog.itemIds);
            close();
            if (created) setOpenId(created.id);
          }}
        />
      );
    }

    if (dialog.kind === 'rename') {
      return (
        <TitlePromptModal
          heading="Rename collection"
          confirmLabel="Rename"
          initialTitle={dialog.title}
          isBusy={collections.isBusy}
          onClose={close}
          onConfirm={async (title) => {
            await collections.rename(dialog.collectionId, title);
            close();
            afterWrite();
          }}
        />
      );
    }

    if (dialog.kind === 'add') {
      return (
        <ItemPickerModal
          title="Add items"
          confirmLabel="Add"
          mediaServerId={mediaServerId}
          libraryId={library.id}
          excludedIds={new Set(dialog.memberIds)}
          isBusy={collections.isBusy}
          onClose={close}
          onConfirm={async (itemIds) => {
            await collections.addItems(dialog.collectionId, itemIds);
            close();
            afterWrite();
          }}
        />
      );
    }

    if (dialog.kind === 'remove') {
      return (
        <ConfirmModal
          title="Remove from collection"
          message={`Remove "${dialog.item.title}" from this collection? The item itself is not deleted.`}
          confirmLabel="Remove"
          onCancel={close}
          onConfirm={async () => {
            await collections.removeItems(dialog.collectionId, [dialog.item.id]);
            close();
            afterWrite();
          }}
        />
      );
    }

    return (
      <ConfirmModal
        title="Delete collection"
        message={`Delete "${dialog.title}" from the media server? The items in it are not deleted. This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onCancel={close}
        onConfirm={async () => {
          await collections.remove(dialog.collectionId);
          close();
          setOpenId(null);
        }}
      />
    );
  }
}

type Dialog =
  | { kind: 'create' }
  | { kind: 'create-name'; itemIds: number[] }
  | { kind: 'rename'; collectionId: number; title: string }
  | { kind: 'delete'; collectionId: number; title: string }
  | { kind: 'add'; collectionId: number; memberIds: number[] }
  | { kind: 'remove'; collectionId: number; item: LibraryItem }
  | { kind: 'match' };
