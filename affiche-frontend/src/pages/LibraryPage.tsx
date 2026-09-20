import { useState, useEffect, useEffectEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Info } from 'lucide-react';
import { Header } from '../components/layout';
import { ItemGrid, ItemTable, ItemDetail, EpisodeList, LibraryRows, LibraryStage, PosterBrowserModal, AlphabetIndex, SelectionBar, posterTargetFromItem, type StagePoster } from '../components/library';
import { ConfirmModal } from '../components/common';
import { errorMessage, libraryApi } from '../api';
import {
  useAlphabetIndex,
  useEventStream,
  useItemLock,
  useItemSelection,
  useLibraryCoverage,
  useLibraryItemCounts,
  useLibraryItems,
  useItemNeighbours,
  useLibraryListing,
  useLibraryRows,
  useLibraryUploadSetting,
  useOpenItem,
  usePosterBrowser,
  useStagePoster,
  useTaskTracking,
} from '../hooks';
import { useToast } from '../context/ToastContext';
import type { Library, LibraryItem, TaskKind } from '../types';
import { libraryPath } from '../routes';
import { LIBRARY_ACTIONS, type LibraryActionName } from './libraryActions';
import { confirmationCopy, type ConfirmAction } from './libraryConfirmations';
import { progressPercent, taskSummary } from './taskSummary';
import styles from './LibraryPage.module.css';

interface LibraryPageProps {
  mediaServerId?: number;
  mediaServerName?: string;
  libraries: Library[];
  allLibraries: Library[];
  selectedLibraryId?: number;
  mode?: 'library' | 'trash';
  onRefreshLibraries: () => void;

  openItemId?: number;

  onOpenItem?: (item: LibraryItem | null) => void;
}

export function LibraryPage({
  mediaServerId,
  mediaServerName,
  libraries,
  allLibraries,
  selectedLibraryId,
  mode = 'library',
  onRefreshLibraries,
  openItemId,
  onOpenItem,
}: LibraryPageProps) {
  const isTrash = mode === 'trash';
  const navigate = useNavigate();
  const toast = useToast();

  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);

  const [resetIncludeUnprocessed, setResetIncludeUnprocessed] = useState(false);

  const {
    searchValue, setSearchValue, debouncedSearch,
    filter, setFilter,
    provider, setProvider,
    sort, setSort,
    viewMode, setViewMode,
  } = useLibraryListing();

  const selectedLibrary = selectedLibraryId
    ? libraries.find((l) => l.id === selectedLibraryId)
    : undefined;

  const showRows = !isTrash && !selectedLibrary;

  const [rowsRefreshKey, setRowsRefreshKey] = useState(0);

  const {
    items, setItems, total, setTotal,
    isLoading, isLoadingMore, hasMore,
    fetchItems, handleLoadMore, loadUpTo,
  } = useLibraryItems({
    mediaServerId,
    libraries,
    selectedLibrary,
    isTrash,
    search: debouncedSearch,
    filter,
    provider,
    sort,
    enabled: !showRows,
  });

  const { counts: filterCounts, reload: reloadFilterCounts } = useLibraryItemCounts({
    libraries,
    selectedLibrary,
    isTrash,
    search: debouncedSearch,
    filter,
    provider,
    enabled: !showRows,
  });

  const {
    isActionLoading, setIsActionLoading,
    taskMessage, setTaskMessage,
    taskKind, taskProgress,
    startTaskTracking, attachRunningTask,
    handleTaskStatus, handleTaskProgress, stopTask,
  } = useTaskTracking({
    onTaskFinished: ({ status, kind }) => {

      fetchItems(true);
      setRowsRefreshKey((key) => key + 1);
      reloadFilterCounts();
      onRefreshLibraries();
      if (status === 'completed') void announceCompletion(kind);
    },
  });

  const announceCompletion = async (kind: TaskKind) => {
    let failedCount: number | undefined;
    if (kind === 'generate' && selectedLibrary) {
      try {
        const counts = await libraryApi.getLibraryItemCounts(selectedLibrary.media_server_id, selectedLibrary.id);
        failedCount = counts.errors;
      } catch {
        failedCount = undefined;
      }
    }
    const summary = taskSummary(kind, selectedLibrary?.name ?? mediaServerName ?? 'All libraries', failedCount);
    toast.success(summary.message, {
      title: summary.title,
      ...(summary.offerFailed
        ? { duration: 12000, action: { label: 'Show failed items', onClick: () => setFilter('errors') } }
        : {}),
    });
  };

  const openItem = useOpenItem({
    allLibraries,
    refreshListing: fetchItems,
    setPageBusy: setIsActionLoading,
    setPageMessage: setTaskMessage,
  });

  const itemLock = useItemLock({
    allLibraries,
    setItems,
    onLockChanged: reloadFilterCounts,
  });

  const coverage = useLibraryCoverage({
    libraryId: selectedLibrary?.id,
    enabled: !showRows && !isTrash,
    refreshKey: rowsRefreshKey,
  });

  const stage = useStagePoster({
    library: selectedLibrary,
    items,
    enabled: !showRows && !isTrash,
  });

  const selection = useItemSelection({
    items,
    mediaServerId,
    onTaskStarted: (taskId) => startTaskTracking(taskId),
    refreshListing: fetchItems,
    listingKey: `${mediaServerId}|${selectedLibraryId ?? 'all'}|${mode}|${debouncedSearch}|${filter}|${provider ?? ''}`,
  });

  const autoUpload = useLibraryUploadSetting({ library: selectedLibrary, enabled: !showRows && !isTrash });

  const handleSelectAllMatching = selectedLibrary
    ? async () => {
        try {
          selection.selectAllMatching(await libraryApi.getLibraryItemIds(
            selectedLibrary.media_server_id, selectedLibrary.id,
            { search: debouncedSearch || undefined, status: filter === 'all' ? undefined : filter, provider },
          ));
        } catch (error) {
          toast.error(errorMessage(error, 'Could not select every matching item.'), { title: 'Selection' });
        }
      }
    : undefined;

  useEventStream({
    onItemProcessed: (libraryId, itemId, processed, posterVersion) => {

      setItems((prev) =>
        prev.map((item) =>
          item.id === itemId && item.library_id === libraryId
            ? { ...item, processed, poster_version: posterVersion, has_poster: posterVersion != null }
            : item
        )
      );

      openItem.applyProcessedEvent(libraryId, itemId, processed, posterVersion);
      if (processed) stage.offerGenerated(libraryId, itemId, posterVersion);
    },
    onLibrarySynced: (syncedMediaServerId, libraryId) => {

      if (syncedMediaServerId !== mediaServerId) return;
      if (selectedLibraryId && libraryId && libraryId !== selectedLibraryId) return;
      fetchItems(true);
      reloadFilterCounts();
      setRowsRefreshKey((key) => key + 1);
    },
    onSeasonProcessed: () => {

      openItem.refreshImages();
    },
    onTaskStatus: handleTaskStatus,
    onTaskProgress: handleTaskProgress,

    onConnected: attachRunningTask,
  });

  const title = selectedLibrary ? selectedLibrary.name : (isTrash ? 'All libraries' : 'Home');

  const closeOpenItem = useEffectEvent(() => {
    if (openItemId === undefined) openItem.open(null);
  });

  useEffect(() => {
    closeOpenItem();
  }, [debouncedSearch, selectedLibraryId, filter, provider, mediaServerId, mode, sort]);

  const followOpenItemId = useEffectEvent(async (itemId: number | undefined) => {
    if (itemId === undefined) {
      if (openItem.item) openItem.close();
      return;
    }
    if (openItem.item?.id === itemId) return;

    const library = selectedLibrary;
    if (!library) return;
    try {
      openItem.open(await libraryApi.getItem(library.media_server_id, library.id, itemId));
    } catch (error) {
      toast.error(errorMessage(error, 'Could not open that item.'), { title: 'Library' });
      onOpenItem?.(null);
    }
  });

  useEffect(() => {
    followOpenItemId(openItemId);
  }, [openItemId]);

  const handleItemClick = (item: LibraryItem) => {
    openItem.open(item);
    onOpenItem?.(item);
  };

  const handleOpenLibrary = (libraryId: number) => {
    if (mediaServerId) navigate(libraryPath(mediaServerId, libraryId));
  };

  const handleBackToListing = () => {
    openItem.close();
    onOpenItem?.(null);
  };

  const libraryRows = useLibraryRows({
    mediaServerId, libraries, enabled: showRows, refreshKey: rowsRefreshKey,
  });

  const alphabet = useAlphabetIndex({
    selectedLibrary,
    isTrash,
    search: debouncedSearch,
    filter,
    provider,
    viewMode,
    sort,
    items,
    loadUpTo,
  });

  const posterBrowser = usePosterBrowser({
    item: openItem.item,
    mediaServerId: openItem.library?.media_server_id,
    onApplied: openItem.applyPosterApplied,
  });

  const handleSyncLibraryClick = () => runLibraryAction('sync');
  const handleSyncPostersClick = () => setConfirmAction('generate');
  const handleUploadPostersClick = () => setConfirmAction('upload');
  const handleResetPostersClick = () => {
    setResetIncludeUnprocessed(false);
    setConfirmAction('reset');
  };

  const runLibraryAction = async (action: LibraryActionName) => {
    setConfirmAction(null);
    if (!mediaServerId) return;

    const spec = LIBRARY_ACTIONS[action];
    try {
      const response = await spec.request({
        mediaServerId,
        library: selectedLibrary,
        includeUnprocessed: resetIncludeUnprocessed,
      });
      startTaskTracking(response.task_id, undefined, spec.taskKind);
    } catch (error) {
      setIsActionLoading(false);
      toast.error(errorMessage(error, spec.errorFallback), { title: spec.errorTitle });
    }
  };

  const openNeighbours = useItemNeighbours({
    library: selectedLibrary,
    item: openItem.item,
    items,
    hasMore,
    listing: { search: debouncedSearch || undefined, status: filter === 'all' ? undefined : filter, provider, sort },
    enabled: !isTrash,
  });

  const listingEmptyMessage = debouncedSearch || filter !== 'all' || provider
    ? { title: 'Nothing matches', hint: 'Try another search, or clear the filters.' }
    : { title: 'No items yet', hint: 'Use Sync library in the ⋮ menu to fetch this library from the media server.' };

  const handleOpenStagePoster = async (poster: StagePoster) => {
    if (!selectedLibrary) return;
    const listed = items.find((i) => i.id === poster.itemId);
    try {
      handleItemClick(listed ?? await libraryApi.getItem(selectedLibrary.media_server_id, poster.libraryId, poster.itemId));
    } catch (error) {
      toast.error(errorMessage(error, 'Could not open that item.'), { title: 'Library' });
    }
  };

  const handleRefreshItems = () => {
    fetchItems();
    reloadFilterCounts();
  };

  const handleRestoreItem = async (item: LibraryItem) => {
    const lib = allLibraries.find((l) => l.id === item.library_id);
    if (!lib) return;

    try {
      await libraryApi.restoreItem(lib.media_server_id, item.library_id, item.id);

      setItems((prev) => prev.filter((i) => !(i.id === item.id && i.library_id === item.library_id)));
      setTotal((prev) => Math.max(0, prev - 1));
      onRefreshLibraries();
    } catch (error) {
      toast.error(errorMessage(error, 'Could not restore this item.'), { title: 'Restore failed' });
    }
  };

  const handleEmptyTrashClick = () => setConfirmAction('empty-trash');

  const executeEmptyTrash = async () => {
    setConfirmAction(null);
    if (!mediaServerId) return;

    const targets = selectedLibrary ? [selectedLibrary] : libraries;

    const results = await Promise.allSettled(
      targets.map((lib) => libraryApi.emptyTrash(lib.media_server_id, lib.id))
    );
    fetchItems();
    onRefreshLibraries();

    const failures = results.filter((r) => r.status === 'rejected');
    if (failures.length > 0) {
      toast.error(
        targets.length === 1
          ? errorMessage(failures[0].reason, 'Could not empty the trash.')
          : `${failures.length} of ${targets.length} libraries could not be emptied.`,
        { title: 'Empty trash' }
      );
    }
  };

  const handleItemGeneratePosterClick = () => openItem.generatePoster();
  const handleItemResetClick = () => setConfirmAction('item-reset');

  const confirmed = (run: () => void) => () => {
    setConfirmAction(null);
    run();
  };

  const confirmHandlers: Record<ConfirmAction, () => void> = {
    'generate': () => runLibraryAction('generate'),
    'upload': () => runLibraryAction('upload'),
    'reset': () => runLibraryAction('reset'),
    'item-reset': confirmed(openItem.resetPoster),
    'selection-generate': confirmed(selection.generate),
    'selection-upload': confirmed(selection.upload),
    'selection-reset': confirmed(selection.reset),
    'empty-trash': executeEmptyTrash,
  };

  const confirmModalProps = (() => {
    if (!confirmAction) return null;
    const copy = confirmationCopy(confirmAction, {
      libraryName: selectedLibrary?.name || 'all libraries',
      itemName: openItem.item?.title || '',
      selectionCount: selection.count,

      pendingCount: selectedLibrary && !debouncedSearch && !provider ? filterCounts?.unprocessed : undefined,
      uploadsAutomatically: autoUpload,
    });
    return {
      ...copy,
      onConfirm: confirmHandlers[confirmAction],

      ...(copy.checkboxLabel
        ? { checkboxChecked: resetIncludeUnprocessed, onCheckboxChange: setResetIncludeUnprocessed }
        : {}),
    };
  })();

  if (!mediaServerId) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyContent}>
          <h2>No media server selected</h2>
          <p>Select a media server from the sidebar or add one in settings.</p>
          <button
            className={styles.emptyButton}
            onClick={() => navigate('/settings?tab=media-servers')}
          >
            Go to settings
          </button>
        </div>
      </div>
    );
  }

  if (libraries.length === 0) {
    return (
      <>
        <Header
          title="No libraries"
          parentLabel={mediaServerName}
          onSyncLibrary={handleSyncLibraryClick}
          onSyncPosters={handleSyncPostersClick}
          onResetPosters={handleResetPostersClick}
          onRefreshItems={handleRefreshItems}
          onStopTask={stopTask}
          isLoading={isActionLoading}
          statusMessage={taskMessage}
          taskKind={taskKind}
          taskProgress={taskProgress}
          searchValue={searchValue}
          onSearchChange={setSearchValue}
        />
        <div className={styles.emptyState}>
          <div className={styles.emptyContent}>
            <h2>No libraries yet</h2>
            <p>This media server has no libraries in Affiche yet.</p>
            <button className={styles.emptyButton} onClick={handleSyncLibraryClick}>
              Sync libraries
            </button>
          </div>
        </div>
        {confirmModalProps && (
          <ConfirmModal
            {...confirmModalProps}
            onCancel={() => setConfirmAction(null)}
          />
        )}
      </>
    );
  }

  if (openItem.item && openItem.season) {
    return (
      <div className={styles.episodePane}>
        <EpisodeList
          showId={openItem.item.id}
          libraryId={openItem.item.library_id}
          showTitle={openItem.item.title}
          seasonNumber={openItem.season.season_number}
          mediaServerId={openItem.library?.media_server_id}
          onBack={() => openItem.openSeason(null)}
        />
      </div>
    );
  }

  if (openItem.item) {
    return (
      <>
        <ItemDetail
          item={openItem.item}
          mediaServerId={openItem.library?.media_server_id}
          mediaServerName={mediaServerName}
          onBack={handleBackToListing}
          previousItem={openNeighbours.previous}
          nextItem={openNeighbours.next}
          onPrevious={openNeighbours.previous ? () => handleItemClick(openNeighbours.previous!) : undefined}
          onNext={openNeighbours.next ? () => handleItemClick(openNeighbours.next!) : undefined}
          onSync={openItem.syncMetadata}
          onGeneratePoster={handleItemGeneratePosterClick}
          uploadsAutomatically={autoUpload}
          onReset={handleItemResetClick}
          onSelectPoster={(posterUrl) => posterBrowser.open(null, posterUrl)}
          onUpload={openItem.uploadPoster}
          onToggleLock={openItem.toggleLock}
          onSeasonSelectPoster={(season) => posterBrowser.open(season)}
          onSeasonClick={openItem.openSeason}
          isLoading={isActionLoading}
          isUploading={openItem.isUploading}
          statusMessage={taskMessage}
          imageRefreshKey={openItem.imageRefreshKey}
        />
        {posterBrowser.isOpen && (
          <PosterBrowserModal
            target={posterTargetFromItem(openItem.item)}
            seasonNumber={posterBrowser.season?.season_number}
            onClose={posterBrowser.close}
            onSave={posterBrowser.save}
            isSaving={posterBrowser.isSaving}
            defaultUpload={posterBrowser.uploadDefault}
            initialPoster={posterBrowser.initialPoster}
          />
        )}
        {confirmModalProps && (
          <ConfirmModal
            {...confirmModalProps}
            onCancel={() => setConfirmAction(null)}
          />
        )}
      </>
    );
  }

  return (
    <>
      <Header
        title={title}
        parentLabel={mediaServerName}
        mode={mode}
        onSyncLibrary={handleSyncLibraryClick}
        onSyncPosters={handleSyncPostersClick}
        onUploadPosters={handleUploadPostersClick}
        onResetPosters={handleResetPostersClick}
        onRefreshItems={handleRefreshItems}
        onEmptyTrash={handleEmptyTrashClick}
        onStopTask={stopTask}
        isLoading={isActionLoading}
        statusMessage={taskMessage}
        taskKind={taskKind}
        taskProgress={taskProgress}
        searchValue={showRows ? undefined : searchValue}
        onSearchChange={showRows ? undefined : setSearchValue}
        filter={showRows ? undefined : filter}
        onFilterChange={showRows ? undefined : setFilter}
        provider={showRows ? undefined : provider}
        onProviderChange={showRows ? undefined : setProvider}
        filterCounts={showRows ? undefined : filterCounts}
        pendingCount={selectedLibrary && !debouncedSearch && !provider ? filterCounts?.unprocessed : undefined}
        viewMode={showRows ? undefined : viewMode}
        onViewModeChange={showRows ? undefined : setViewMode}
        selectMode={showRows ? undefined : selection.isSelectMode}
        onToggleSelectMode={showRows ? undefined : selection.toggleSelectMode}
      />
      {isTrash && (
        <div className={styles.trashNotice}>
          <Info size={15} />
          <span>
            These are Affiche's own records for items it can no longer find on the media server.
            Restoring or purging them only changes Affiche's database — your media server is never
            modified.
          </span>
        </div>
      )}
      {
}
      {!showRows && (selection.isSelectMode || selection.count > 0) && (
        <SelectionBar
          count={selection.count}
          allSelected={items.length > 0 && items.every((item) => selection.isSelected(item.id))}
          matchingTotal={isTrash ? undefined : total}
          isAllMatching={selection.isAllMatching}
          onSelectAllMatching={isTrash ? undefined : handleSelectAllMatching}
          isBusy={selection.isBusy}
          onToggleAll={selection.toggleAll}
          onClear={selection.clear}
          onGenerate={() => setConfirmAction('selection-generate')}
          onUpload={() => setConfirmAction('selection-upload')}
          onLock={selection.lock}
          onUnlock={selection.unlock}
          onReset={() => setConfirmAction('selection-reset')}
        />
      )}
      {!showRows && !isTrash && selectedLibrary && (
        <LibraryStage
          libraryName={selectedLibrary.name}
          poster={stage.poster}
          stats={coverage}
          autoUpload={autoUpload}
          serverName={mediaServerName}
          onChangeAutoUpload={() => navigate('/settings?tab=media-servers')}
          runPercent={isActionLoading && taskKind === 'generate' ? progressPercent(taskProgress) : null}
          onOpenPoster={handleOpenStagePoster}
        />
      )}
      {showRows ? (
        <LibraryRows
          rows={libraryRows.rows}
          isLoading={libraryRows.isLoading}
          onItemClick={handleItemClick}
          onOpenLibrary={handleOpenLibrary}
        />
      ) : viewMode === 'list' ? (
        <ItemTable
          items={items}
          onItemClick={isTrash ? undefined : handleItemClick}
          isLoading={isLoading}
          hasMore={hasMore}
          onLoadMore={handleLoadMore}
          isLoadingMore={isLoadingMore}
          variant={isTrash ? 'trash' : 'default'}
          emptyMessage={listingEmptyMessage}
          onRestore={isTrash ? handleRestoreItem : undefined}
          sort={sort}
          onSortChange={setSort}
          onToggleSelect={isTrash ? undefined : (item, extend) => selection.toggle(item.id, extend)}
          onToggleSelectAll={selection.toggleAll}
          isSelected={(item) => selection.isSelected(item.id)}
          selectMode={selection.isSelectMode}
          onToggleLock={isTrash ? undefined : itemLock.toggle}
          isLockPending={itemLock.isPending}
        />
      ) : (
        <ItemGrid
          items={items}
          onItemClick={isTrash ? undefined : handleItemClick}
          isLoading={isLoading}
          hasMore={hasMore}
          onLoadMore={handleLoadMore}
          isLoadingMore={isLoadingMore}
          variant={isTrash ? 'trash' : 'default'}
          emptyMessage={listingEmptyMessage}
          onRestore={isTrash ? handleRestoreItem : undefined}
          showAnchors={alphabet.isEnabled}
          onToggleSelect={isTrash ? undefined : (item, extend) => selection.toggle(item.id, extend)}
          isSelected={(item) => selection.isSelected(item.id)}
          selectMode={selection.isSelectMode}
          onToggleLock={isTrash ? undefined : itemLock.toggle}
          isLockPending={itemLock.isPending}
        />
      )}
      {alphabet.isEnabled && alphabet.entries.length > 0 && (
        <AlphabetIndex entries={alphabet.entries} onLetterClick={alphabet.handleLetterClick} />
      )}
      {confirmModalProps && (
        <ConfirmModal
          {...confirmModalProps}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </>
  );
}
