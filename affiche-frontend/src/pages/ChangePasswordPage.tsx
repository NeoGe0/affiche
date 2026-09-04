import { useState, type FormEvent } from 'react';
import { errorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { AfficheLogo } from '../components/common';
import styles from './AuthPage.module.css';

export function ChangePasswordPage() {
  const { changePassword, username } = useAuth();
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    setSubmitting(true);
    try {
      await changePassword(current, password);

    } catch (err) {
      setError(errorMessage(err, 'Could not change the password'));
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <div className={styles.brand}>
          <AfficheLogo size={30} />
          <span className={styles.brandText}>
            A<span className={styles.brandDouble}>ff</span>iche
          </span>
        </div>
        <p className={styles.subtitle}>
          {username ? `Choose a new password for ${username}` : 'Choose a new password'}
        </p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <p className={styles.notice}>
            This account is signed in with a temporary password, which was written to the server
            log. Choose a new one to use Affiche.
          </p>
          {error && <div className={styles.error}>{error}</div>}
          <div className={styles.field}>
            <label className={styles.label} htmlFor="current-password">Temporary password</label>
            <input
              id="current-password"
              className={styles.input}
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="new-password">New password</label>
            <input
              id="new-password"
              className={styles.input}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="confirm-password">Confirm new password</label>
            <input
              id="confirm-password"
              className={styles.input}
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
          <button className={styles.submit} type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : 'Set password'}
          </button>
        </form>
      </div>
    </div>
  );
}
