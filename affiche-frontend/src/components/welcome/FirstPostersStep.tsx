import { useState } from 'react';
import { Loader2 } from 'lucide-react';

import { errorMessage, libraryApi } from '../../api';
import { useLibraryUploadSetting } from '../../hooks';
import type { Library } from '../../types';
import styles from './Welcome.module.css';

interface FirstPostersStepProps {
  libraries: Library[];

  onStarted: (library: Library) => void;
}

export function FirstPostersStep({ libraries, onStarted }: FirstPostersStepProps) {
  const [libraryId, setLibraryId] = useState<number | undefined>(libraries[0]?.id);
  const [status, setStatus] = useState<'idle' | 'generating' | 'syncing'>('idle');
  const [error, setError] = useState<string | null>(null);

  const library = libraries.find((l) => l.id === libraryId) ?? libraries[0];
  const uploads = useLibraryUploadSetting({ library, enabled: !!library });

  const start = async (generate: boolean) => {
    if (!library) return;
    setStatus(generate ? 'generating' : 'syncing');
    setError(null);
    try {
      await (generate
        ? libraryApi.syncLibraryPosters(library.media_server_id, library.id)
        : libraryApi.syncLibrary(library.media_server_id, library.id));
      onStarted(library);
    } catch (err) {
      setError(errorMessage(err, 'The run could not be started.'));
      setStatus('idle');
    }
  };

  if (!library) {
    return <p className={styles.hint}>No library was added. Add one in Settings → Media servers.</p>;
  }

  return (
    <>
      <div className={styles.field}>
        <label htmlFor="welcome-first-library">Library</label>
        <select
          id="welcome-first-library"
          value={library.id}
          onChange={(e) => setLibraryId(Number(e.target.value))}
        >
          {libraries.map((l) => (
            <option key={l.id} value={l.id}>{l.name}</option>
          ))}
        </select>
      </div>
      {}
      {uploads !== undefined && (
        <p className={styles.hint}>
          {uploads
            ? `${library.name} uploads new posters to your media server as they are made, keeping its current artwork for Reset.`
            : `${library.name} keeps new posters in Affiche until you upload them.`}
        </p>
      )}

      {error && <p className={styles.error} role="alert">{error}</p>}

      <div className={styles.row}>
        <button type="button" className={styles.primary} onClick={() => start(true)} disabled={status !== 'idle'}>
          {status === 'generating' && <Loader2 size={16} className="spin" />}
          Generate posters
        </button>
        <button type="button" className={styles.linkButton} onClick={() => start(false)} disabled={status !== 'idle'}>
          {status === 'syncing' && <Loader2 size={16} className="spin" />}
          Only read the library for now
        </button>
      </div>
    </>
  );
}
