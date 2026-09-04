import { useEffect, useEffectEvent, useState, type FormEvent } from 'react';
import { KeyRound, Pencil, Plus, Trash2, User } from 'lucide-react';

import { authApi, errorMessage } from '../../api';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { ConfirmModal } from '../common';
import type { UserAccount, UserRole } from '../../types';
import { ROLE_LABEL } from './roles';
import { UserAccountModal } from './UserAccountModal';
import sectionStyles from './SettingsSection.module.css';
import styles from './UsersSettings.module.css';

export function UsersSettings() {
  const { username, role, isAdmin, changePassword } = useAuth();
  const toast = useToast();

  const [accounts, setAccounts] = useState<UserAccount[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<UserAccount | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editing, setEditing] = useState<UserAccount | null | undefined>(undefined);

  const loadAccounts = useEffectEvent(async () => {
    if (!isAdmin) return;
    try {
      setAccounts(await authApi.listUsers());
    } catch (error) {
      toast.error(errorMessage(error, 'Could not load the accounts'), { title: 'Users' });
    }
  });

  useEffect(() => {
    void loadAccounts();
  }, [isAdmin]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await authApi.deleteUser(deleteTarget.id);
      setAccounts((prev) => prev.filter((account) => account.id !== deleteTarget.id));
      setDeleteTarget(null);
      toast.success(`Removed ${deleteTarget.username}`);
    } catch (error) {

      toast.error(errorMessage(error, 'Could not remove the account'), { title: 'Users' });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <section className={sectionStyles.section}>
      <div className={sectionStyles.sectionHeader}>
        <div>
          <h2 className={sectionStyles.sectionTitle}>Users</h2>
          <p className={sectionStyles.sectionDescription}>
            Accounts that can sign in to Affiche.
          </p>
        </div>
      </div>

      <AccountCard username={username} role={role} onChangePassword={changePassword} />

      {isAdmin && (
        <AccountList
          accounts={accounts}
          currentUsername={username}
          onAdd={() => setEditing(null)}
          onEdit={setEditing}
          onRemove={setDeleteTarget}
        />
      )}

      {editing !== undefined && (
        <UserAccountModal
          account={editing ?? undefined}
          onSaved={(saved) =>
            setAccounts((prev) => prev.some((a) => a.id === saved.id)
              ? prev.map((a) => (a.id === saved.id ? saved : a))
              : [...prev, saved])
          }
          onClose={() => setEditing(undefined)}
        />
      )}

      {deleteTarget && (
        <ConfirmModal
          title="Remove account"
          message={`Remove "${deleteTarget.username}"? They will be signed out and will no longer be able to sign in. Nothing they generated is deleted.`}
          confirmLabel={isDeleting ? 'Removing...' : 'Remove'}
          variant="danger"
          isBusy={isDeleting}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </section>
  );
}

interface AccountCardProps {
  username: string | null;
  role: UserRole | null;
  onChangePassword: (current: string, next: string) => Promise<void>;
}

function AccountCard({ username, role, onChangePassword }: AccountCardProps) {
  const toast = useToast();
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const canSubmit = Boolean(current && password && confirm) && !isSaving;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    if (password !== confirm) {
      toast.error('The new password and its confirmation are different.', { title: 'Password' });
      return;
    }
    setIsSaving(true);
    try {
      await onChangePassword(current, password);

      setCurrent('');
      setPassword('');
      setConfirm('');
      toast.success('Password changed. Every other session was signed out.');
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to change the password'), { title: 'Password' });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className={sectionStyles.card}>
      <div className={styles.identity}>
        <User size={18} className={styles.identityIcon} />
        <span className={styles.identityName}>{username ?? 'Signed in'}</span>
        {role && <RoleBadge role={role} />}
        <span className={styles.identityHint}>This is you</span>
      </div>

      <form className={styles.block} onSubmit={handleSubmit}>
        <div className={styles.blockHeader}>
          <KeyRound size={16} className={styles.blockIcon} />
          <span className={styles.blockTitle}>Change password</span>
        </div>
        <p className={styles.blockHint}>Signs every other session out, and keeps this one.</p>

        <div className={styles.form}>
          <Field id="account-current-password" label="Current password" autoComplete="current-password"
                 value={current} onChange={setCurrent} disabled={isSaving} />
          <Field id="account-new-password" label="New password" autoComplete="new-password"
                 value={password} onChange={setPassword} disabled={isSaving} />
          <Field id="account-confirm-password" label="Confirm new password" autoComplete="new-password"
                 value={confirm} onChange={setConfirm} disabled={isSaving} />
          <button
            type="submit"
            className={`${sectionStyles.outlineButton} ${sectionStyles.outlineButtonAccent}`}
            disabled={!canSubmit}
          >
            {isSaving ? 'Saving...' : 'Change password'}
          </button>
        </div>
      </form>
    </div>
  );
}

interface AccountListProps {
  accounts: UserAccount[];
  currentUsername: string | null;
  onAdd: () => void;
  onEdit: (account: UserAccount) => void;
  onRemove: (account: UserAccount) => void;
}

function AccountList({
  accounts, currentUsername, onAdd, onEdit, onRemove,
}: AccountListProps) {
  return (
    <div className={`${sectionStyles.card} ${styles.listCard}`}>
      <div className={styles.listHeader}>
        <span className={styles.blockTitle}>All accounts</span>
        <button
          type="button"
          className={`${sectionStyles.outlineButton} ${sectionStyles.outlineButtonSmall} ${sectionStyles.outlineButtonAccent}`}
          onClick={onAdd}
        >
          <Plus size={14} /> Add user
        </button>
      </div>

      <ul className={styles.accounts}>
        {accounts.map((account) => (
          <li key={account.id} className={styles.account}>
            <User size={16} className={styles.identityIcon} />
            <span className={styles.accountName}>{account.username}</span>
            <RoleBadge role={account.role} />
            {

}
            {account.username === currentUsername ? (
              <span className={styles.identityHint}>This is you</span>
            ) : (
              <span className={styles.rowActions}>
                <button
                  type="button"
                  className={styles.rowAction}
                  onClick={() => onEdit(account)}
                  aria-label={`Edit ${account.username}`}
                >
                  <Pencil size={15} />
                </button>
                <button
                  type="button"
                  className={`${styles.rowAction} ${styles.remove}`}
                  onClick={() => onRemove(account)}
                  aria-label={`Remove ${account.username}`}
                >
                  <Trash2 size={15} />
                </button>
              </span>
            )}
          </li>
        ))}
      </ul>

    </div>
  );
}

function RoleBadge({ role }: { role: UserRole }) {
  return (
    <span className={`${styles.badge} ${role === 'ADMIN' ? styles.badgeAdmin : ''}`}>
      {ROLE_LABEL[role]}
    </span>
  );
}

interface FieldProps {
  id: string;
  label: string;
  autoComplete: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}

function Field({ id, label, autoComplete, value, onChange, disabled }: FieldProps) {
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>{label}</label>
      <input
        id={id}
        className={styles.input}
        type="password"
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />
    </div>
  );
}
