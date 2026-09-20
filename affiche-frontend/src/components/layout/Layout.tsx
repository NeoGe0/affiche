import { useEffect, useState, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { useMediaQuery } from '../../hooks';
import { GlobalSearchModal } from '../search';
import type { Library, MediaServerResponse, SearchHit } from '../../types';
import styles from './Layout.module.css';

const NARROW_QUERY = '(max-width: 899px)';

interface MediaServerWithLibraries {
  server: MediaServerResponse;
  libraries: Library[];
}

interface LayoutProps {
  children: ReactNode;
  mediaServers: MediaServerWithLibraries[];
  selectedMediaServerId?: number;
  selectedLibraryId?: number;
  view?: 'library' | 'trash' | 'collections';
  onSelectLibrary: (mediaServerId: number, libraryId: number | undefined) => void;
  onSelectTrash: (mediaServerId: number, libraryId: number | undefined) => void;
  onSelectCollections: (mediaServerId: number, libraryId: number | undefined) => void;

  onOpenSearchHit: (hit: SearchHit) => void;
}

export function Layout({
  children,
  mediaServers,
  selectedMediaServerId,
  selectedLibraryId,
  view = 'library',
  onSelectLibrary,
  onSelectTrash,
  onSelectCollections,
  onOpenSearchHit,
}: LayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const isNarrow = useMediaQuery(NARROW_QUERY);
  const [overlayOpen, setOverlayOpen] = useState(false);
  const location = useLocation();
  const [prevLocation, setPrevLocation] = useState(location);
  if (location !== prevLocation) {

    setPrevLocation(location);
    setOverlayOpen(false);
  }
  const isOverlayShown = isNarrow && overlayOpen;

  useEffect(() => {
    if (!isOverlayShown) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOverlayOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [isOverlayShown]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === 'k' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        setIsSearchOpen(true);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  return (
    <div className={styles.layout}>
      <Sidebar
        mediaServers={mediaServers}
        selectedMediaServerId={selectedMediaServerId}
        selectedLibraryId={selectedLibraryId}
        view={view}
        collapsed={isNarrow || collapsed}
        overlayOpen={isOverlayShown}
        onToggleCollapse={() => (isNarrow ? setOverlayOpen((open) => !open) : setCollapsed((c) => !c))}
        onSelectLibrary={onSelectLibrary}
        onSelectTrash={onSelectTrash}
        onSelectCollections={onSelectCollections}
        onOpenSearch={() => setIsSearchOpen(true)}
      />
      {isOverlayShown && (
        <div className={styles.overlayBackdrop} onClick={() => setOverlayOpen(false)} aria-hidden="true" />
      )}
      <main className={`${styles.main} ${isNarrow || collapsed ? styles.mainCollapsed : ''}`}>{children}</main>
      {isSearchOpen && (
        <GlobalSearchModal
          onClose={() => setIsSearchOpen(false)}
          onSelect={onOpenSearchHit}
        />
      )}
    </div>
  );
}
