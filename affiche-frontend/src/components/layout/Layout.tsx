import { useEffect, useState, type ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { GlobalSearchModal } from '../search';
import type { Library, MediaServerResponse, SearchHit } from '../../types';
import styles from './Layout.module.css';

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
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(c => !c)}
        onSelectLibrary={onSelectLibrary}
        onSelectTrash={onSelectTrash}
        onSelectCollections={onSelectCollections}
        onOpenSearch={() => setIsSearchOpen(true)}
      />
      <main className={`${styles.main} ${collapsed ? styles.mainCollapsed : ''}`}>{children}</main>
      {isSearchOpen && (
        <GlobalSearchModal
          onClose={() => setIsSearchOpen(false)}
          onSelect={onOpenSearchHit}
        />
      )}
    </div>
  );
}
