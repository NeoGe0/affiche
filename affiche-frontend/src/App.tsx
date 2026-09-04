import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Layout } from './components/layout';
import { ChangePasswordPage, CollectionsPage, DashboardPage, LibraryPage, SettingsPage, LoginPage, SetupPage } from './pages';
import { libraryApi, mediaServerApi } from './api';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { ThemeProvider } from './context/ThemeContext';
import type { Library, MediaServerResponse, SearchHit } from './types';
import { libraryPath, listingPath, parseLocation } from './routes';
import styles from './App.module.css';

interface MediaServerWithLibraries {
  server: MediaServerResponse;
  libraries: Library[];
}

function AppContent() {
  const [mediaServers, setMediaServers] = useState<MediaServerWithLibraries[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const { serverId: selectedMediaServerId, libraryId: selectedLibraryId, view, itemId } =
    parseLocation(useLocation().pathname);

  const fetchData = useCallback(async () => {
    try {
      const servers = await mediaServerApi.getAll();

      const serversWithLibraries: MediaServerWithLibraries[] = await Promise.all(
        servers.map(async (server) => {
          try {
            return { server, libraries: await libraryApi.getLibraries(server.id) };
          } catch (error) {
            console.error(`Failed to fetch libraries for server ${server.id}:`, error);
            return { server, libraries: [] };
          }
        })
      );
      setMediaServers(serversWithLibraries);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSelectLibrary = (mediaServerId: number, libraryId: number | undefined) =>
    navigate(libraryPath(mediaServerId, libraryId));

  const handleOpenSearchHit = (hit: SearchHit) =>
    navigate(libraryPath(hit.media_server_id, hit.library_id, hit.id));

  const handleSelectCollections = (mediaServerId: number, libraryId: number | undefined) =>
    navigate(listingPath('collections', mediaServerId, libraryId));

  const handleSelectTrash = (mediaServerId: number, libraryId: number | undefined) =>
    navigate(listingPath('trash', mediaServerId, libraryId));

  const handleOpenItem = (item: { id: number; library_id: number } | null) => {
    if (!selectedMediaServerId) return;
    navigate(item
      ? listingPath(view, selectedMediaServerId, item.library_id, item.id)
      : listingPath(view, selectedMediaServerId, selectedLibraryId));
  };

  const allLibraries = mediaServers.flatMap(ms => ms.libraries);

  const defaultServerId = mediaServers[0]?.server.id;

  const selectedServer = selectedMediaServerId
    ? mediaServers.find(ms => ms.server.id === selectedMediaServerId)
    : undefined;
  const selectedServerLibraries = selectedServer?.libraries || [];

  if (isLoading) {
    return <CenteredMessage>Loading...</CenteredMessage>;
  }

  return (
    <Layout
      mediaServers={mediaServers}
      selectedMediaServerId={selectedMediaServerId}
      selectedLibraryId={selectedLibraryId}
      view={view}
      onSelectLibrary={handleSelectLibrary}
      onSelectTrash={handleSelectTrash}
      onSelectCollections={handleSelectCollections}
      onOpenSearchHit={handleOpenSearchHit}
    >
      <Routes>
        {

}
        {(['libraries/:libraryId', 'libraries/:libraryId/items/:itemId'] as const).map((path) => (
          <Route
            key={path}
            path={`servers/:serverId/${path}`}
            element={
              <LibraryPage
                mediaServerId={selectedMediaServerId}
                mediaServerName={selectedServer?.server.name}
                libraries={selectedServerLibraries}
                allLibraries={allLibraries}
                selectedLibraryId={selectedLibraryId}
                openItemId={itemId}
                onOpenItem={handleOpenItem}
                onRefreshLibraries={fetchData}
              />
            }
          />
        ))}
        {}
        <Route
          path="servers/:serverId/trash/:libraryId"
          element={
            <LibraryPage
              mediaServerId={selectedMediaServerId}
              mediaServerName={selectedServer?.server.name}
              libraries={selectedServerLibraries}
              allLibraries={allLibraries}
              selectedLibraryId={selectedLibraryId}
              mode="trash"
              onRefreshLibraries={fetchData}
            />
          }
        />
        <Route
          path="servers/:serverId/collections/:libraryId"
          element={
            <CollectionsPage
              mediaServerId={selectedMediaServerId}
              mediaServerName={selectedServer?.server.name}
              libraries={selectedServerLibraries}
              selectedLibraryId={selectedLibraryId}
            />
          }
        />
        <Route
          path="dashboard"
          element={<DashboardPage onOpenLibrary={handleSelectLibrary} />}
        />
        <Route path="settings" element={<SettingsPage onDataChanged={fetchData} />} />
        {
}
        <Route
          path="*"
          element={defaultServerId
            ? <Navigate to={libraryPath(defaultServerId)} replace />
            : <CenteredMessage>No media server configured yet.</CenteredMessage>}
        />
      </Routes>
    </Layout>
  );
}

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return <div className={styles.centered}>{children}</div>;
}

function AppRoutes() {
  const { loading, isAuthenticated, setupRequired, passwordChangeRequired } = useAuth();

  if (loading) {
    return <CenteredMessage>Loading…</CenteredMessage>;
  }

  if (isAuthenticated && passwordChangeRequired) {
    return <ChangePasswordPage />;
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? <Navigate to="/" replace />
            : setupRequired ? <Navigate to="/setup" replace />
            : <LoginPage />
        }
      />
      <Route
        path="/setup"
        element={
          setupRequired ? <SetupPage />
            : isAuthenticated ? <Navigate to="/" replace />
            : <Navigate to="/login" replace />
        }
      />
      <Route
        path="/*"
        element={
          isAuthenticated ? <AppContent />
            : setupRequired ? <Navigate to="/setup" replace />
            : <Navigate to="/login" replace />
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      {
}
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
