import { NavLink, useLocation } from 'react-router-dom';
import { Settings, Bell, ChevronDown, ChevronRight, Cloud, Home, Layers, LayoutDashboard, Library, HardDrive, Palette, Search, SwatchBook, Type, SlidersHorizontal, Trash2, Users, PanelLeftClose, PanelLeft, LogOut } from 'lucide-react';
import { useState } from 'react';
import type { Library as LibraryType, MediaServerResponse } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useAppVersion } from '../../hooks';
import { SOURCE_URL } from '../../constants/app';
import { AfficheLogo, LibraryTypeIcon, MediaServerIcon } from '../common';
import styles from './Sidebar.module.css';

interface MediaServerWithLibraries {
  server: MediaServerResponse;
  libraries: LibraryType[];
}

interface SidebarProps {
  mediaServers: MediaServerWithLibraries[];
  selectedMediaServerId?: number;
  selectedLibraryId?: number;
  view?: 'library' | 'trash' | 'collections';
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onSelectLibrary: (mediaServerId: number, libraryId: number | undefined) => void;
  onSelectTrash: (mediaServerId: number, libraryId: number | undefined) => void;
  onSelectCollections: (mediaServerId: number, libraryId: number | undefined) => void;
  onOpenSearch: () => void;
}

export function Sidebar({
  mediaServers,
  selectedMediaServerId,
  selectedLibraryId,
  view = 'library',
  collapsed = false,
  onToggleCollapse,
  onSelectLibrary,
  onSelectTrash,
  onSelectCollections,
  onOpenSearch,
}: SidebarProps) {
  const { username, isAdmin, logout } = useAuth();
  const { version, isPrerelease } = useAppVersion();
  const location = useLocation();
  const isSettingsPage = location.pathname.startsWith('/settings');
  const searchParams = new URLSearchParams(location.search);
  const currentTab = searchParams.get('tab') || 'media-servers';
  const currentSection = searchParams.get('section');

  const isStyleSection = (section: string) =>
    isSettingsPage && currentTab === 'style' && currentSection === section;

  const isLibraryView = !isSettingsPage && view === 'library';
  const isTrashView = !isSettingsPage && view === 'trash';
  const isCollectionsView = !isSettingsPage && view === 'collections';

  const [expandedServers, setExpandedServers] = useState<Set<number>>(
    () => new Set(selectedMediaServerId ? [selectedMediaServerId] : [])
  );
  const [prevSelectedServerId, setPrevSelectedServerId] = useState(selectedMediaServerId);

  const [expandedTrash, setExpandedTrash] = useState<Set<number>>(new Set());
  const [expandedCollections, setExpandedCollections] = useState<Set<number>>(new Set());
  const [mediaServersExpanded, setMediaServersExpanded] = useState(true);
  const [settingsExpanded, setSettingsExpanded] = useState(isSettingsPage);

  const [peek, setPeek] = useState(false);

  if (selectedMediaServerId !== prevSelectedServerId) {
    setPrevSelectedServerId(selectedMediaServerId);
    if (selectedMediaServerId) {
      setExpandedServers(prev => new Set(prev).add(selectedMediaServerId));
    }
  }

  const toggleServer = (serverId: number) => {
    setExpandedServers(prev => {
      const next = new Set(prev);
      if (next.has(serverId)) {
        next.delete(serverId);
      } else {
        next.add(serverId);
      }
      return next;
    });
  };

  const toggleCollections = (serverId: number) => {
    setExpandedCollections((prev) => {
      const next = new Set(prev);
      if (!next.delete(serverId)) next.add(serverId);
      return next;
    });
  };

  const toggleTrash = (serverId: number) => {
    setExpandedTrash(prev => {
      const next = new Set(prev);
      if (next.has(serverId)) {
        next.delete(serverId);
      } else {
        next.add(serverId);
      }
      return next;
    });
  };

  const hasMediaServers = mediaServers.length > 0;

  return (
    <>
      {
}
      {collapsed && (
        <div
          className={styles.rail}
          onMouseEnter={() => setPeek(true)}
        >
          <NavLink to="/" className={styles.railLogo} title="Home">
            <AfficheLogo size={22} />
          </NavLink>
          <div className={styles.railDivider} />
          <button
            className={styles.railButton}
            onClick={onOpenSearch}
            title="Search all libraries"
            aria-label="Search all libraries"
          >
            <Search size={20} />
          </button>
          <NavLink
            to="/dashboard"
            className={({ isActive }) => `${styles.railButton} ${isActive ? styles.active : ''}`}
            title="Dashboard"
            aria-label="Dashboard"
          >
            <LayoutDashboard size={20} />
          </NavLink>
          <button
            className={styles.railButton}
            onClick={onToggleCollapse}
            title="Media Servers"
            aria-label="Media Servers"
          >
            <HardDrive size={20} />
          </button>
          <button
            className={styles.railButton}
            onClick={onToggleCollapse}
            title="Settings"
            aria-label="Settings"
          >
            <Settings size={20} />
          </button>
          <button
            className={`${styles.railButton} ${styles.railExpand}`}
            onClick={onToggleCollapse}
            title="Expand menu"
            aria-label="Expand menu"
          >
            <PanelLeft size={20} />
          </button>
          <button
            className={styles.railButton}
            onClick={logout}
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={20} />
          </button>
        </div>
      )}
      <aside
        className={`${styles.sidebar} ${collapsed ? styles.collapsed : ''} ${collapsed && peek ? styles.peek : ''}`}
        onMouseLeave={() => setPeek(false)}
      >
      <div className={styles.logo}>
        <NavLink to="/" className={styles.logoBrand} title="Home">
          <span className={styles.logoMark}>
            <AfficheLogo size={22} />
          </span>
          <span className={styles.logoText}>
            A<span className={styles.logoDouble}>ff</span>iche
          </span>
        </NavLink>
        <button
          className={styles.collapseButton}
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand menu' : 'Collapse menu'}
          aria-label={collapsed ? 'Expand menu' : 'Collapse menu'}
        >
          {collapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <nav className={styles.nav}>
        <div className={styles.section}>
          <button className={styles.sectionHeader} onClick={onOpenSearch}>
            <Search size={18} />
            <span>Search</span>
            {
}
            <kbd className={styles.shortcut}>Ctrl K</kbd>
          </button>
        </div>

        <div className={styles.section}>
          <NavLink
            to="/dashboard"
            className={({ isActive }) => `${styles.sectionHeader} ${isActive ? styles.active : ''}`}
          >
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </NavLink>
        </div>

        <div className={styles.section}>
          <button
            className={styles.sectionHeader}
            onClick={() => setMediaServersExpanded(!mediaServersExpanded)}
          >
            <HardDrive size={18} />
            <span>Media Servers</span>
            {mediaServersExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>

          {mediaServersExpanded && (
            <div className={styles.serverList}>
              {!hasMediaServers ? (
                <div className={styles.emptyState}>
                  <span>No media servers</span>
                  <NavLink to="/settings?tab=media-servers" className={styles.addLink}>
                    Add one
                  </NavLink>
                </div>
              ) : (
                mediaServers.map(({ server, libraries: serverLibraries }) => {
                  const libs = serverLibraries || [];
                  const isExpanded = expandedServers.has(server.id);
                  const isServerSelected = selectedMediaServerId === server.id && isLibraryView;
                  const isTrashExpanded = expandedTrash.has(server.id);
                  const isServerTrashSelected = selectedMediaServerId === server.id && isTrashView;

                  return (
                    <div key={server.id} className={styles.serverGroup}>
                      <button
                        className={`${styles.serverHeader} ${isServerSelected && selectedLibraryId === undefined ? styles.active : ''}`}
                        onClick={() => toggleServer(server.id)}
                      >
                        <MediaServerIcon type={server.type} />
                        <span className={styles.serverName}>{server.name}</span>
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </button>

                      {isExpanded && (
                        <ul className={styles.libraryList}>
                          <li>
                            <button
                              className={`${styles.libraryItem} ${isServerSelected && selectedLibraryId === undefined ? styles.active : ''}`}
                              onClick={() => onSelectLibrary(server.id, undefined)}
                            >
                              <Home size={14} />
                              <span>Home</span>
                              <span className={styles.count}>
                                {libs.reduce((sum, lib) => sum + (lib.media_count || 0), 0)}
                              </span>
                            </button>
                          </li>
                          {libs.map((lib) => (
                            <li key={lib.id}>
                              <button
                                className={`${styles.libraryItem} ${selectedLibraryId === lib.id && isLibraryView ? styles.active : ''}`}
                                onClick={() => onSelectLibrary(server.id, lib.id)}
                              >
                                <LibraryTypeIcon type={lib.library_type} />
                                <span>{lib.name}</span>
                                <span className={styles.count}>{lib.media_count || 0}</span>
                              </button>
                            </li>
                          ))}
                          {libs.length === 0 && (
                            <li className={styles.emptyLibraries}>
                              No libraries synced
                            </li>
                          )}

                          {

}
                          <li>
                            <button
                              className={`${styles.libraryItem} ${isCollectionsView ? styles.active : ''}`}
                              onClick={() => toggleCollections(server.id)}
                            >
                              <Layers size={14} />
                              <span>Collections</span>
                              {expandedCollections.has(server.id)
                                ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            </button>
                            {expandedCollections.has(server.id) && (
                              <ul className={styles.trashList}>
                                {libs.map((lib) => (
                                  <li key={lib.id}>
                                    <button
                                      className={`${styles.trashItem} ${selectedLibraryId === lib.id && isCollectionsView ? styles.active : ''}`}
                                      onClick={() => onSelectCollections(server.id, lib.id)}
                                    >
                                      <LibraryTypeIcon type={lib.library_type} />
                                      <span>{lib.name}</span>
                                    </button>
                                  </li>
                                ))}
                                {libs.length === 0 && (
                                  <li className={styles.emptyLibraries}>No libraries synced</li>
                                )}
                              </ul>
                            )}
                          </li>

                          {
}
                          <li>
                            <button
                              className={`${styles.libraryItem} ${isServerTrashSelected && selectedLibraryId === undefined ? styles.active : ''}`}
                              onClick={() => toggleTrash(server.id)}
                            >
                              <Trash2 size={14} />
                              <span>Trash</span>
                              {isTrashExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            </button>
                            {isTrashExpanded && (
                              <ul className={styles.trashList}>
                                <li>
                                  <button
                                    className={`${styles.trashItem} ${isServerTrashSelected && selectedLibraryId === undefined ? styles.active : ''}`}
                                    onClick={() => onSelectTrash(server.id, undefined)}
                                  >
                                    <Library size={14} />
                                    <span>All Libraries</span>
                                  </button>
                                </li>
                                {libs.map((lib) => (
                                  <li key={lib.id}>
                                    <button
                                      className={`${styles.trashItem} ${selectedLibraryId === lib.id && isTrashView ? styles.active : ''}`}
                                      onClick={() => onSelectTrash(server.id, lib.id)}
                                    >
                                      <LibraryTypeIcon type={lib.library_type} />
                                      <span>{lib.name}</span>
                                    </button>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </li>
                        </ul>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

        <div className={styles.section}>
          <button
            className={`${styles.sectionHeader} ${isSettingsPage ? styles.active : ''}`}
            onClick={() => setSettingsExpanded(!settingsExpanded)}
          >
            <Settings size={18} />
            <span>Settings</span>
            {settingsExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>

          {settingsExpanded && (
            <ul className={styles.subMenu}>
              {isAdmin && (
              <li>
                <NavLink
                  to="/settings?tab=general"
                  className={`${styles.subMenuItem} ${isSettingsPage && currentTab === 'general' ? styles.active : ''}`}
                >
                  <SlidersHorizontal size={16} />
                  <span>General</span>
                </NavLink>
              </li>
              )}
              {isAdmin && (
              <li>
                <NavLink
                  to="/settings?tab=media-servers"
                  className={`${styles.subMenuItem} ${isSettingsPage && currentTab === 'media-servers' ? styles.active : ''}`}
                >
                  <HardDrive size={16} />
                  <span>Media Servers</span>
                </NavLink>
              </li>
              )}
              {isAdmin && (
              <li>
                <NavLink
                  to="/settings?tab=apis"
                  className={`${styles.subMenuItem} ${isSettingsPage && currentTab === 'apis' ? styles.active : ''}`}
                >
                  <Cloud size={16} />
                  <span>Poster APIs</span>
                </NavLink>
              </li>
              )}
              {isAdmin && (
              <li>
                <NavLink
                  to="/settings?tab=notifications"
                  className={`${styles.subMenuItem} ${isSettingsPage && currentTab === 'notifications' ? styles.active : ''}`}
                >
                  <Bell size={16} />
                  <span>Notifications</span>
                </NavLink>
              </li>
              )}
              <li>
                <NavLink
                  to="/settings?tab=users"
                  className={`${styles.subMenuItem} ${isSettingsPage && currentTab === 'users' ? styles.active : ''}`}
                >
                  <Users size={16} />
                  <span>Users</span>
                </NavLink>
              </li>
              {isAdmin && (
              <li>
                <NavLink
                  to="/settings?tab=style"
                  className={`${styles.subMenuItem} ${isSettingsPage && currentTab === 'style' && !currentSection ? styles.active : ''}`}
                >
                  <Palette size={16} />
                  <span>Style Options</span>
                </NavLink>
                {

}
                <ul className={styles.subMenu}>
                  <li>
                    <NavLink
                      to="/settings?tab=style&section=fonts"
                      className={`${styles.subSubMenuItem} ${isStyleSection('fonts') ? styles.active : ''}`}
                    >
                      <Type size={14} />
                      <span>Fonts</span>
                    </NavLink>
                  </li>
                  <li>
                    <NavLink
                      to="/settings?tab=style&section=profiles"
                      className={`${styles.subSubMenuItem} ${isStyleSection('profiles') ? styles.active : ''}`}
                    >
                      <SwatchBook size={14} />
                      <span>Style Profiles</span>
                    </NavLink>
                  </li>
                </ul>
              </li>
              )}
            </ul>
          )}
        </div>
      </nav>

      <div className={styles.footer}>
        <button className={styles.logoutButton} onClick={logout} title="Sign out">
          <LogOut size={16} />
          <span className={styles.logoutLabel}>
            {username ? `Sign out (${username})` : 'Sign out'}
          </span>
        </button>
        {version && (
          <div className={styles.version}>
            <span className={styles.versionNumber}>v{version}</span>
            {isPrerelease && <span className={styles.betaTag}>Beta</span>}
            {}
            <a
              className={styles.sourceLink}
              href={SOURCE_URL}
              target="_blank"
              rel="noreferrer"
            >
              Source
            </a>
          </div>
        )}
      </div>
      </aside>
    </>
  );
}
