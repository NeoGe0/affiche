import { useState } from 'react';
import { CheckCircle, Loader2 } from 'lucide-react';

import { errorMessage, mediaServerApi } from '../../api';
import type { MediaServerTestResult, MediaServerType } from '../../types';
import { MediaServerIcon } from '../common';
import { SERVER_CONFIG } from '../settings/mediaServerHelpers';
import styles from './Welcome.module.css';

const PLEX_TOKEN_HELP = 'https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/';

interface ConnectServerStepProps {

  onCreated: () => void;
}

export function ConnectServerStep({ onCreated }: ConnectServerStepProps) {
  const [serverType, setServerType] = useState<MediaServerType>('PLEX');
  const [url, setUrl] = useState(SERVER_CONFIG.PLEX.url);
  const [token, setToken] = useState('');
  const [found, setFound] = useState<MediaServerTestResult | null>(null);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [status, setStatus] = useState<'idle' | 'connecting' | 'saving'>('idle');
  const [error, setError] = useState<string | null>(null);

  const forget = () => {
    setFound(null);
    setError(null);
  };

  const chooseType = (type: MediaServerType) => {
    if (type === serverType) return;
    setServerType(type);
    setUrl(SERVER_CONFIG[type].url);
    setToken('');
    forget();
  };

  const connect = async () => {
    setStatus('connecting');
    forget();
    try {
      const result = serverType === 'PLEX'
        ? await mediaServerApi.testPlex(url, token)
        : await mediaServerApi.testJellyfin(url, token);
      setFound(result);
      setSelected(new Set(result.libraries.map((library) => library.id)));
    } catch (err) {
      setError(errorMessage(err, `Could not reach ${SERVER_CONFIG[serverType].name} at that address.`));
    } finally {
      setStatus('idle');
    }
  };

  const save = async () => {
    if (!found) return;
    setStatus('saving');
    setError(null);
    try {
      await mediaServerApi.create({
        name: found.name,
        type: serverType,
        url,
        token,
        enabled: true,
        libraries: found.libraries.filter((library) => selected.has(library.id)),
      });
      onCreated();
    } catch (err) {
      setError(errorMessage(err, 'The server could not be saved.'));
      setStatus('idle');
    }
  };

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  };

  const config = SERVER_CONFIG[serverType];
  const count = selected.size;

  return (
    <>
      <div className={styles.choices} role="group" aria-label="Media server type">
        {(Object.keys(SERVER_CONFIG) as MediaServerType[]).map((type) => (
          <button
            key={type}
            type="button"
            className={styles.choice}
            aria-pressed={serverType === type}
            onClick={() => chooseType(type)}
          >
            <MediaServerIcon type={type} size={24} />
            <span>
              <span className={styles.choiceName}>{SERVER_CONFIG[type].name}</span>
              <span className={styles.choiceHint}>Needs {type === 'PLEX' ? 'a Plex token' : 'an API key'}</span>
            </span>
          </button>
        ))}
      </div>

      <div className={styles.fields}>
        <div className={styles.field}>
          <label htmlFor="welcome-server-url">Server address</label>
          <input
            id="welcome-server-url"
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); forget(); }}
            placeholder={config.url}
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="welcome-server-token">{serverType === 'PLEX' ? 'Plex token' : 'API key'}</label>
          <input
            id="welcome-server-token"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(e) => { setToken(e.target.value); forget(); }}
            placeholder={config.tokenPlaceholder}
          />
        </div>
      </div>
      <p className={styles.hint}>
        {serverType === 'PLEX' ? (
          <>Where to find it: <a href={PLEX_TOKEN_HELP} target="_blank" rel="noreferrer">Finding your Plex token</a>.</>
        ) : (
          'Create one in Jellyfin under Dashboard → API Keys.'
        )}
      </p>

      {error && <p className={styles.error} role="alert">{error}</p>}

      {found ? (
        <>
          <p className={styles.ok}>
            <CheckCircle size={16} /> Connected to “{found.name}” — {found.libraries.length}{' '}
            {found.libraries.length === 1 ? 'library' : 'libraries'} found
          </p>
          <div className={styles.libraries} role="group" aria-label="Libraries to add">
            {found.libraries.map((library) => (
              <label key={library.id} className={styles.library}>
                <input type="checkbox" checked={selected.has(library.id)} onChange={() => toggle(library.id)} />
                {library.name}
                <span className={styles.libraryCount}>{library.item_count.toLocaleString()} items</span>
              </label>
            ))}
          </div>
          <div className={styles.row}>
            <button
              type="button"
              className={styles.primary}
              onClick={save}
              disabled={count === 0 || status === 'saving'}
            >
              {status === 'saving' && <Loader2 size={16} className="spin" />}
              Add server and {count} {count === 1 ? 'library' : 'libraries'}
            </button>
          </div>
        </>
      ) : (
        <div className={styles.row}>
          <button
            type="button"
            className={styles.primary}
            onClick={connect}
            disabled={!url.trim() || !token.trim() || status === 'connecting'}
          >
            {status === 'connecting' && <Loader2 size={16} className="spin" />}
            Connect
          </button>
        </div>
      )}
    </>
  );
}
