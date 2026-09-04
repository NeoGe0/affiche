import { RefreshCw, Image, RotateCcw, ListRestart, Loader, Search, X, StopCircle, Trash2, Upload, LayoutGrid, List, CheckSquare } from 'lucide-react';
import { OverflowMenu, TaskProgressBar, type OverflowMenuItem } from '../common';

import { FilterMenu } from '../library/FilterMenu';
import type {
  ItemFilter, LibraryItemCounts, TaskKind, TaskProgressState, ViewMode,
} from '../../types';
import { runningActionLabel, runningTaskVerb } from './headerTask';
import styles from './Header.module.css';

interface HeaderProps {
  title: string;

  parentLabel?: string;

  mode?: 'library' | 'trash';
  onSyncLibrary: () => void;
  onSyncPosters: () => void;
  onUploadPosters?: () => void;
  onResetPosters: () => void;
  onRefreshItems?: () => void;
  onEmptyTrash?: () => void;
  onStopTask?: () => void;
  isLoading?: boolean;
  statusMessage?: string | null;

  taskKind?: TaskKind | null;

  taskProgress?: TaskProgressState | null;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  filter?: ItemFilter;
  onFilterChange?: (filter: ItemFilter) => void;

  provider?: string;
  onProviderChange?: (provider: string | undefined) => void;

  filterCounts?: LibraryItemCounts;

  viewMode?: ViewMode;
  onViewModeChange?: (mode: ViewMode) => void;

  selectMode?: boolean;
  onToggleSelectMode?: () => void;
}

export function Header({
  title,
  parentLabel,
  mode = 'library',
  onSyncLibrary,
  onSyncPosters,
  onUploadPosters,
  onResetPosters,
  onRefreshItems,
  onEmptyTrash,
  onStopTask,
  isLoading,
  statusMessage,
  taskKind,
  taskProgress,
  searchValue = '',
  onSearchChange,
  filter = 'all',
  onFilterChange,
  provider,
  onProviderChange,
  filterCounts,
  viewMode = 'grid',
  onViewModeChange,
  selectMode = false,
  onToggleSelectMode,
}: HeaderProps) {
  const isTrash = mode === 'trash';
  const pct = taskProgress && taskProgress.total > 0
    ? Math.min(100, Math.round((taskProgress.current / taskProgress.total) * 100))
    : null;

  const runningLabel = isLoading ? runningActionLabel(taskKind, pct) : null;

  const showProgressBar = isLoading && pct != null && runningTaskVerb(taskKind) != null;

  const menuItems: OverflowMenuItem[] = [
    { icon: <RefreshCw size={16} />, label: 'Sync library', onClick: onSyncLibrary,
      disabled: isLoading },
    ...(onRefreshItems
      ? [{ icon: <ListRestart size={16} />, label: 'Refresh items', onClick: onRefreshItems }]
      : []),
    ...(onUploadPosters
      ? [{ icon: <Upload size={16} />, label: 'Upload posters', onClick: onUploadPosters,
           disabled: isLoading }]
      : []),
    { icon: <RotateCcw size={16} />, label: 'Reset posters', onClick: onResetPosters,
      disabled: isLoading, danger: true },
  ];

  return (
    <header className={styles.header}>
      <div className={styles.titleSection}>
        <h1 className={styles.title}>
          {parentLabel && (
            <>
              <span className={styles.crumbParent}>{parentLabel}</span>
              <span className={styles.crumbSep}>/</span>
            </>
          )}
          {
}
          <span className={styles.titleText}>{title}</span>
          {isTrash && <span className={styles.crumbBadge}>· Trash</span>}
        </h1>
        {
}
        {isLoading && !showProgressBar && statusMessage && (
          <div className={styles.status}>
            <Loader size={14} className={styles.spinning} />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>

      <div className={styles.centerSection}>
        {!isTrash && onFilterChange && onProviderChange && (
          <FilterMenu
            filter={filter}
            onFilterChange={onFilterChange}
            provider={provider}
            onProviderChange={onProviderChange}
            counts={filterCounts}
          />
        )}

        {onSearchChange && (
          <div className={styles.searchContainer}>
            <Search size={16} className={styles.searchIcon} />
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Search items..."
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
            />
            {searchValue && (
              <button
                className={styles.clearSearch}
                onClick={() => onSearchChange('')}
                title="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </div>
        )}

        {!isTrash && onViewModeChange && (
          <div className={styles.viewToggle} role="group" aria-label="View mode">
            <button
              className={`${styles.viewButton} ${viewMode === 'grid' ? styles.viewButtonActive : ''}`}
              onClick={() => onViewModeChange('grid')}
              title="Grid view"
              aria-pressed={viewMode === 'grid'}
            >
              <LayoutGrid size={16} />
            </button>
            <button
              className={`${styles.viewButton} ${viewMode === 'list' ? styles.viewButtonActive : ''}`}
              onClick={() => onViewModeChange('list')}
              title="List view"
              aria-pressed={viewMode === 'list'}
            >
              <List size={16} />
            </button>
          </div>
        )}

        {!isTrash && onToggleSelectMode && (
          <button
            className={`${styles.viewButton} ${styles.selectToggle} ${selectMode ? styles.viewButtonActive : ''}`}
            onClick={onToggleSelectMode}
            title={selectMode ? 'Leave select mode' : 'Select multiple items'}
            aria-pressed={selectMode}
          >
            <CheckSquare size={16} />
            <span>Select</span>
          </button>
        )}
      </div>

      <div className={styles.actions}>
        {isTrash ? (
          onEmptyTrash && (
            <button
              className={`${styles.actionButton} ${styles.danger}`}
              onClick={onEmptyTrash}
              disabled={isLoading}
              title="Permanently delete all items in this trash"
            >
              <Trash2 size={16} />
              <span>Empty trash</span>
            </button>
          )
        ) : (

          <>
            <button
              className={`${styles.actionButton} ${styles.primary} ${styles.runAction}`}
              onClick={onSyncPosters}
              disabled={isLoading}
              title={runningLabel ?? 'Generate decorated posters'}
            >
              {runningLabel
                ? <Loader size={16} className={styles.spinning} />
                : <Image size={16} />}
              <span>{runningLabel ?? 'Generate Posters'}</span>
            </button>

            {isLoading && onStopTask ? (
              <button
                className={`${styles.actionButton} ${styles.stop}`}
                onClick={onStopTask}
                title="Stop current task"
              >
                <StopCircle size={16} />
              </button>
            ) : (
              <OverflowMenu
                items={menuItems}
                title="Library actions"
                triggerClassName={`${styles.actionButton} ${styles.iconOnly}`}
              />
            )}
          </>
        )}
      </div>

      {
}
      {showProgressBar && <TaskProgressBar progress={taskProgress} />}
    </header>
  );
}
