import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  ConnectServerStep,
  currentWelcomeStep,
  FirstPostersStep,
  PosterSourcesStep,
  SetupStep,
  stepState,
} from '../components/welcome';
import { providerLabel } from '../constants/providers';
import { useAuth } from '../context/AuthContext';
import type { Library, MediaServerResponse } from '../types';
import styles from './WelcomePage.module.css';

interface WelcomePageProps {
  mediaServers: { server: MediaServerResponse; libraries: Library[] }[];

  onDataChanged: () => void;
  onOpenLibrary: (mediaServerId: number, libraryId: number) => void;
}

export function WelcomePage({ mediaServers, onDataChanged, onOpenLibrary }: WelcomePageProps) {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [sourcesConfirmed, setSourcesConfirmed] = useState(false);
  const [sourcesSummary, setSourcesSummary] = useState<string | null>(null);

  const first = mediaServers[0];
  const libraries = mediaServers.flatMap((entry) => entry.libraries);
  const current = currentWelcomeStep(!!first, sourcesConfirmed);

  if (!isAdmin) {
    return (
      <div className={styles.page}>
        <div className={styles.memberNotice}>
          <h2>Nothing to show yet</h2>
          <p>
            Affiche has no media server connected. Only an admin can connect one — once they have,
            your libraries appear here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <h2>Let's get your first posters made</h2>
        <p>Three steps. Each one can be changed later in Settings.</p>
      </header>

      <ol className={styles.steps}>
        <SetupStep
          number={1}
          title="Connect your media server"
          summary={first
            ? `${first.server.name} · ${first.libraries.map((l) => l.name).join(', ') || 'no libraries'}`
            : 'Affiche reads your libraries from it and writes the posters back.'}
          state={stepState('server', current)}
          onChange={() => navigate('/settings?tab=media-servers')}
        >
          <ConnectServerStep onCreated={onDataChanged} />
        </SetupStep>

        <SetupStep
          number={2}
          title="Choose where posters come from"
          summary={sourcesConfirmed && sourcesSummary
            ? sourcesSummary
            : 'Where Affiche looks for artwork. More can be added in Settings → Poster APIs.'}
          state={stepState('sources', current)}
          onChange={() => setSourcesConfirmed(false)}
        >
          <PosterSourcesStep
            libraries={libraries}
            onDone={(providers) => {
              setSourcesSummary(providers.map(providerLabel).join(' and '));
              setSourcesConfirmed(true);
            }}
          />
        </SetupStep>

        <SetupStep
          number={3}
          title="Make your first posters"
          summary="Affiche reads the library, then makes a poster for each title in the default style."
          state={stepState('posters', current)}
        >
          <FirstPostersStep
            libraries={libraries}
            onStarted={(library) => onOpenLibrary(library.media_server_id, library.id)}
          />
        </SetupStep>
      </ol>
    </div>
  );
}
