import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { configApi, errorMessage, serviceApi } from '../../api';
import { POSTER_PROVIDER_CARDS, type PosterProvider } from '../../constants/providers';
import type { Library, ServiceConfiguration } from '../../types';
import { PROVIDER_ICONS } from '../settings/providerIcons';
import { missingTmdbWarning } from './welcomeSteps';
import styles from './Welcome.module.css';

const card = (name: PosterProvider) => POSTER_PROVIDER_CARDS.find((c) => c.serviceName === name)!;
const TMDB = card('tmdb');
const TVMAZE = card('tvmaze');

interface PosterSourcesStepProps {

  libraries: Library[];

  onDone: (providers: PosterProvider[]) => void;
}

export function PosterSourcesStep({ libraries, onDone }: PosterSourcesStepProps) {
  const [configs, setConfigs] = useState<ServiceConfiguration[] | null>(null);
  const [tmdbToken, setTmdbToken] = useState('');
  const [status, setStatus] = useState<'idle' | 'checking' | 'saving'>('idle');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    configApi
      .findConfigs('PROVIDER')
      .then((found) => { if (!cancelled) setConfigs(found); })
      .catch(() => { if (!cancelled) setConfigs([]); });
    return () => { cancelled = true; };
  }, []);

  const stored = (name: string) => configs?.find((config) => config.name === name);
  const tmdbReady = !!stored('tmdb')?.configured;
  const warning = missingTmdbWarning(libraries, tmdbReady);

  const checkTmdb = async () => {
    const token = tmdbToken.trim();
    setStatus('checking');
    setError(null);
    try {
      await serviceApi.testProvider('tmdb', token, TMDB.defaultUrl);
      const saved = await configApi.createConfig({
        name: 'tmdb', type: 'PROVIDER', url: TMDB.defaultUrl, token, enabled: true,
      });
      setConfigs((prev) => [...(prev ?? []).filter((c) => c.name !== 'tmdb'), saved]);
      setTmdbToken('');
    } catch (err) {
      setError(errorMessage(err, 'TMDB did not accept that token. Copy the "API Read Access Token", not the API key.'));
    } finally {
      setStatus('idle');
    }
  };

  const done = async () => {
    setStatus('saving');
    setError(null);
    try {
      if (!stored('tvmaze')) {
        await configApi.createConfig({ name: 'tvmaze', type: 'PROVIDER', url: TVMAZE.defaultUrl, enabled: true });
      }
      onDone(tmdbReady ? ['tmdb', 'tvmaze'] : ['tvmaze']);
    } catch (err) {
      setError(errorMessage(err, 'TVmaze could not be turned on.'));
      setStatus('idle');
    }
  };

  if (configs === null) {
    return <Loader2 size={20} className="spin" aria-label="Loading poster sources" />;
  }

  return (
    <>
      <div className={styles.providers}>
        <div className={styles.provider}>
          <span className={styles.providerIcon} style={{ color: TVMAZE.accentColor }}>{PROVIDER_ICONS.tvmaze}</span>
          <div>
            <p className={styles.providerName}>TVmaze</p>
            <p className={styles.providerText}>Series artwork. No key needed.</p>
          </div>
          <span className={`${styles.tag} ${styles.tagReady}`}>Ready</span>
        </div>

        <div className={styles.provider}>
          <span className={styles.providerIcon} style={{ color: TMDB.accentColor }}>{PROVIDER_ICONS.tmdb}</span>
          <div>
            <p className={styles.providerName}>TMDB</p>
            <p className={styles.providerText}>
              The main source for films and series. Free token from{' '}
              <a href={TMDB.getKeyUrl} target="_blank" rel="noreferrer">themoviedb.org</a>.
            </p>
          </div>
          <span className={`${styles.tag} ${tmdbReady ? styles.tagReady : ''}`}>{tmdbReady ? 'Ready' : 'Suggested'}</span>
          {!tmdbReady && (
            <div className={styles.keyRow}>
              <input
                type="password"
                autoComplete="off"
                aria-label="TMDB API read access token"
                placeholder="Paste your TMDB API read access token"
                value={tmdbToken}
                onChange={(e) => setTmdbToken(e.target.value)}
              />
              <button
                type="button"
                className={styles.secondary}
                onClick={checkTmdb}
                disabled={!tmdbToken.trim() || status !== 'idle'}
              >
                {status === 'checking' && <Loader2 size={16} className="spin" />}
                Check and save
              </button>
            </div>
          )}
        </div>
      </div>
      <p className={styles.hint}>TheTVDB, Fanart.tv, MediUX and Shoko can be added in Settings → Poster APIs.</p>

      {error && <p className={styles.error} role="alert">{error}</p>}

      <div className={styles.row}>
        <button type="button" className={styles.primary} onClick={done} disabled={status !== 'idle'}>
          {status === 'saving' && <Loader2 size={16} className="spin" />}
          Continue
        </button>
        {warning && <span className={styles.warning}>{warning}</span>}
      </div>
    </>
  );
}
