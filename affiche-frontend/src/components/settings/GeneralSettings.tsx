import { useState, useEffect, useEffectEvent } from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import { errorMessage, settingsApi } from '../../api';
import { useToast } from '../../context/ToastContext';
import type { AppSettings, AppSettingsInfo } from '../../types';
import sectionStyles from './SettingsSection.module.css';
import styles from './GeneralSettings.module.css';

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];

export function GeneralSettings() {
  const toast = useToast();

  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [info, setInfo] = useState<AppSettingsInfo | null>(null);
  const [savedMsg, setSavedMsg] = useState(false);

  const [loadFailed, setLoadFailed] = useState(false);

  const [retentionDraft, setRetentionDraft] = useState<string | null>(null);

  const load = useEffectEvent(async () => {
    try {
      setSettings(await settingsApi.getSettings());
    } catch (err) {
      setLoadFailed(true);
      toast.error(errorMessage(err, 'Failed to load settings.'), { title: 'General settings' });
    }

    try {
      setInfo(await settingsApi.getSettingsInfo());
    } catch {
      setInfo(null);
    }
  });

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!savedMsg) return;
    const timer = setTimeout(() => setSavedMsg(false), 2000);
    return () => clearTimeout(timer);
  }, [savedMsg]);

  const persist = async (changes: Partial<AppSettings>) => {
    try {
      const updated = await settingsApi.updateSettings(changes);
      setSettings(updated);
      setSavedMsg(true);
      return updated;
    } catch (err) {
      toast.error(errorMessage(err, 'Failed to save settings.'), { title: 'General settings' });
      throw err;
    }
  };

  if (!settings) {
    return (
      <section className={sectionStyles.section}>
        <h2 className={sectionStyles.sectionTitle}>General</h2>
        <div className={sectionStyles.emptyState}>
          {loadFailed ? 'Could not load settings.' : 'Loading settings…'}
        </div>
      </section>
    );
  }

  return (
    <section className={sectionStyles.section}>
      <h2 className={sectionStyles.sectionTitle}>
        General
        {savedMsg && <span className={sectionStyles.savedMsg}>Saved</span>}
      </h2>
      <p className={sectionStyles.sectionDescription}>
        App-wide preferences and diagnostics. Defaults for newly added libraries live with the
        libraries themselves, under Media Servers.
      </p>

      {}
      <div className={sectionStyles.group}>
        <h3 className={sectionStyles.groupTitle}>Logging</h3>
        <p className={sectionStyles.groupDescription}>
          Verbosity of application logs. DEBUG is useful for troubleshooting.
        </p>
        <div className={sectionStyles.row}>
          <label className={sectionStyles.label} htmlFor="log-level">Log level</label>
          <select
            id="log-level"
            className={sectionStyles.select}
            value={settings.log_level}
            onChange={(e) => persist({ log_level: e.target.value })}
          >
            {LOG_LEVELS.map((lvl) => (
              <option key={lvl} value={lvl}>{lvl}</option>
            ))}
          </select>
        </div>
      </div>

      {}
      <div className={sectionStyles.group}>
        <h3 className={sectionStyles.groupTitle}>Trash</h3>
        <p className={sectionStyles.groupDescription}>
          When an item disappears from your media server, Affiche soft-deletes its own record and
          keeps it in that library's trash. Records are purged after this many days (0 purges on the
          next sync); emptying a library's trash purges them immediately. Purging only clears
          Affiche's database — it never deletes anything from your media server.
        </p>
        <div className={sectionStyles.row}>
          <label className={sectionStyles.label} htmlFor="trash-retention">Retention (days)</label>
          <input
            id="trash-retention"
            type="number"
            min={0}
            className={sectionStyles.select}
            value={retentionDraft ?? String(settings.trash_retention_days)}
            onChange={(e) => setRetentionDraft(e.target.value)}
            onBlur={() => {

              const n = parseInt(retentionDraft ?? '', 10);
              if (!Number.isNaN(n) && n >= 0 && n !== settings.trash_retention_days) {
                persist({ trash_retention_days: n }).catch(() => {});
              }
              setRetentionDraft(null);
            }}
          />
        </div>
      </div>

      {}
      <div className={sectionStyles.group}>
        <h3 className={sectionStyles.groupTitle}>Security</h3>
        <p className={sectionStyles.groupDescription}>Encryption of stored media-server tokens at rest.</p>
        <div className={sectionStyles.row}>
          <span className={sectionStyles.label}>Token encryption key</span>
          {info ? (
            info.encryption_key_secure ? (
              <span className={`${styles.badge} ${styles.badgeSecure}`}>
                <ShieldCheck size={14} /> Secure key set
              </span>
            ) : (
              <span className={`${styles.badge} ${styles.badgeInsecure}`}>
                <ShieldAlert size={14} /> Using insecure default
              </span>
            )
          ) : (
            <span className={styles.badge}>Unknown</span>
          )}
        </div>
        {info && !info.encryption_key_secure && (
          <p className={styles.mutedNote}>
            Set the <code>ENCRYPTION_KEY</code> environment variable so stored tokens are encrypted with
            a private key (see .env.example).
          </p>
        )}
      </div>

      {}
      <div className={sectionStyles.group}>
        <h3 className={sectionStyles.groupTitle}>About</h3>
        <div className={sectionStyles.row}>
          <span className={sectionStyles.label}>Version</span>
          <span className={styles.infoValue}>{info?.version ?? '—'}</span>
        </div>
        <div className={sectionStyles.row}>
          <span className={sectionStyles.label}>Database</span>
          <span className={styles.infoValue}>{info?.database ?? '—'}</span>
        </div>
      </div>
    </section>
  );
}
