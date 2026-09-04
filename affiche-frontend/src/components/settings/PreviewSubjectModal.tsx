import { useEffect, useState } from 'react';
import { Loader, Search } from 'lucide-react';

import { errorMessage, libraryApi, mediaServerApi } from '../../api';
import { useLibraryItems } from '../../hooks';
import { Modal } from '../common';
import { libraryOptions, previewSubjectFromItem, type PreviewSubject } from './previewSubject';
import type { Library } from '../../types';
import styles from './PreviewSubjectModal.module.css';

const SORT = { by: 'title', dir: 'asc' } as const;
const NO_LIBRARIES: Library[] = [];

const SEARCH_DEBOUNCE_MS = 300;

interface PreviewSubjectModalProps {
  onClose: () => void;
  onSelect: (subject: PreviewSubject) => void;
}

export function PreviewSubjectModal({ onClose, onSelect }: PreviewSubjectModalProps) {
  const [servers, setServers] = useState<{ id: number; name: string }[]>([]);
  const [libraries, setLibraries] = useState<Library[]>(NO_LIBRARIES);
  const [isLoadingLibraries, setIsLoadingLibraries] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [libraryId, setLibraryId] = useState<number | null>(null);

  const [searchValue, setSearchValue] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const loadedServers = await mediaServerApi.getAll();
        const perServer = await Promise.all(
          loadedServers.map((server) => libraryApi.getLibraries(server.id))
        );
        if (cancelled) return;
        setServers(loadedServers.map(({ id, name }) => ({ id, name })));
        setLibraries(perServer.flat());
      } catch (err) {
        if (!cancelled) setLoadError(errorMessage(err, 'Failed to load libraries'));
      } finally {
        if (!cancelled) setIsLoadingLibraries(false);
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchValue), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchValue]);

  const options = libraryOptions(servers, libraries);

  const activeId = libraryId ?? options[0]?.id ?? null;
  const selectedLibrary = libraries.find((library) => library.id === activeId);

  const { items, isLoading, isLoadingMore, hasMore, handleLoadMore } = useLibraryItems({
    mediaServerId: selectedLibrary?.media_server_id,
    libraries,
    selectedLibrary,
    isTrash: false,
    search: debouncedSearch,
    filter: 'all',
    sort: SORT,
  });

  const isSearching = searchValue !== debouncedSearch;

  return (
    <Modal
      size="large"
      label="Preview title"
      title="Preview title"
      description={'Pick the movie or show the preview is drawn on. Its source artwork is fetched '
        + 'from your poster providers, so the preview shows what generation would produce.'}
      onClose={onClose}
      footer={
        <button className={styles.cancelButton} onClick={onClose}>
          Cancel
        </button>
      }
    >
      <div className={styles.filters}>
        <div className={styles.controls}>
          <select
            className={styles.librarySelect}
            value={activeId ?? ''}
            disabled={options.length === 0}
            onChange={(e) => setLibraryId(Number(e.target.value))}
          >
            {options.length === 0 && <option value="">No libraries</option>}
            {options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>

          <div className={styles.searchWrapper}>
            <Search size={15} className={styles.searchIcon} />
            <input
              type="search"
              className={styles.searchInput}
              placeholder="Filter by title…"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
            />
          </div>
        </div>
      </div>
      <div className={styles.body}>
        {loadError && <p className={styles.error}>{loadError}</p>}

        {isLoadingLibraries || isLoading ? (
          <div className={styles.state}>
            <Loader size={18} className={styles.spinning} />
            <span>Loading…</span>
          </div>
        ) : options.length === 0 ? (
          <div className={styles.state}>
            Add a media server under Settings → Media Servers to pick a title.
          </div>
        ) : items.length === 0 ? (
          <div className={styles.state}>
            {debouncedSearch ? `Nothing matching “${debouncedSearch}”.` : 'This library is empty.'}
          </div>
        ) : (
          <ul className={`${styles.list} ${isSearching ? styles.listStale : ''}`}>
            {items.map((item) => (
              <li key={item.id}>
                <button
                  className={styles.item}
                  onClick={() => {
                    onSelect(previewSubjectFromItem(item));
                    onClose();
                  }}
                >
                  <span className={styles.itemTitle}>{item.title}</span>
                  {item.year !== undefined && <span className={styles.itemMeta}>{item.year}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}

        {hasMore && !isLoading && (
          <button className={styles.loadMore} onClick={handleLoadMore} disabled={isLoadingMore}>
            {isLoadingMore ? 'Loading…' : 'Load more'}
          </button>
        )}
      </div>
    </Modal>
  );
}
