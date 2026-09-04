import { useEffect, useRef, useState } from 'react';
import { CornerDownLeft, Search } from 'lucide-react';

import { libraryApi } from '../../api';
import { Modal, LibraryTypeIcon, MediaServerIcon } from '../common';
import { useGlobalSearch } from '../../hooks';
import { moveHighlight } from './searchHighlight';
import type { SearchHit } from '../../types';
import styles from './GlobalSearchModal.module.css';

interface GlobalSearchModalProps {
  onClose: () => void;
  onSelect: (hit: SearchHit) => void;
}

export function GlobalSearchModal({ onClose, onSelect }: GlobalSearchModalProps) {
  const [term, setTerm] = useState('');
  const [highlight, setHighlight] = useState(0);
  const { hits, total, isLoading, error, isActive, isTruncated, minTermLength } =
    useGlobalSearch(term);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    queueMicrotask(() => inputRef.current?.focus());
  }, []);

  const [previousHits, setPreviousHits] = useState(hits);
  if (previousHits !== hits) {
    setPreviousHits(hits);
    setHighlight(0);
  }

  const select = (hit: SearchHit) => {
    onSelect(hit);
    onClose();
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {

      event.preventDefault();
      const hit = hits[highlight];
      if (hit) select(hit);
      return;
    }

    const next = moveHighlight(hits.length, highlight, event.key);
    if (next === null) return;

    event.preventDefault();
    setHighlight(next);
    listRef.current?.children[next]?.scrollIntoView({ block: 'nearest' });
  };

  return (
    <Modal size="wide" label="Search all libraries" onClose={onClose}>
      <div className={styles.searchBar}>
        <Search size={18} className={styles.searchIcon} />
        <input
          ref={inputRef}
          type="search"
          className={styles.input}
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search every library…"
          aria-label="Search every library"

          aria-describedby="global-search-hint"
        />
      </div>

      <div className={styles.results}>
        {error ? (
          <p className={styles.message} role="alert">{error}</p>
        ) : !isActive ? (
          <p className={styles.message}>
            Type at least {minTermLength} characters to search every library.
          </p>
        ) : isLoading && hits.length === 0 ? (
          <p className={styles.message}>Searching…</p>
        ) : hits.length === 0 ? (
          <p className={styles.message}>No item matches “{term.trim()}”.</p>
        ) : (
          <ul className={styles.list} ref={listRef}>
            {hits.map((hit, index) => (
              <li key={`${hit.library_id}-${hit.id}`}>
                <HitRow
                  hit={hit}
                  isHighlighted={index === highlight}
                  onSelect={() => select(hit)}
                  onHover={() => setHighlight(index)}
                />
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className={styles.hint} id="global-search-hint">
        <span>↑↓ to move, <CornerDownLeft size={12} /> to open</span>
        {isTruncated && (
          <span className={styles.truncated}>
            Showing {hits.length} of {total} matches — narrow the search to see the rest.
          </span>
        )}
      </p>
    </Modal>
  );
}

interface HitRowProps {
  hit: SearchHit;
  isHighlighted: boolean;
  onSelect: () => void;
  onHover: () => void;
}

function HitRow({ hit, isHighlighted, onSelect, onHover }: HitRowProps) {

  const posterUrl = hit.has_poster
    ? libraryApi.getItemPosterUrl(hit.library_id, hit.id, hit.poster_version, 'thumb')
    : null;

  return (
    <button
      type="button"
      className={`${styles.hit} ${isHighlighted ? styles.highlighted : ''}`}
      onClick={onSelect}
      onMouseMove={onHover}
    >
      <span className={styles.poster}>
        {posterUrl ? (
          <img src={posterUrl} alt="" loading="lazy" />
        ) : (
          <LibraryTypeIcon type={hit.library_type} size={16} />
        )}
      </span>
      <span className={styles.details}>
        <span className={styles.title}>
          {hit.title}
          {hit.year != null && <span className={styles.year}> ({hit.year})</span>}
        </span>
        <span className={styles.scope}>
          <MediaServerIcon type={hit.media_server_type} size={12} />
          {hit.media_server_name}
          <span className={styles.separator}>·</span>
          {hit.library_name}
        </span>
      </span>
    </button>
  );
}
