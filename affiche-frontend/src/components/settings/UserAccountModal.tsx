import { useId, useState, type FormEvent } from 'react';

import { authApi, errorMessage } from '../../api';
import { Modal } from '../common';
import { useToast } from '../../context/ToastContext';
import type { UserAccount, UserRole } from '../../types';
import { ROLE_LABEL, ROLE_SUMMARY } from './roles';
import sectionStyles from './SettingsSection.module.css';
import styles from './UserAccountModal.module.css';

const ROLES: UserRole[] = ['OPERATOR', 'ADMIN'];

interface UserAccountModalProps {

  account?: UserAccount;
  onSaved: (account: UserAccount) => void;
  onClose: () => void;
}

export function UserAccountModal({ account, onSaved, onClose }: UserAccountModalProps) {
  const toast = useToast();
  const uid = useId();
  const isEdit = account !== undefined;

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>(account?.role ?? 'OPERATOR');
  const [isSaving, setIsSaving] = useState(false);

  const canSubmit = isSaving
    ? false
    : isEdit
      ? role !== account.role
      : Boolean(username.trim() && password);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setIsSaving(true);
    try {
      const saved = isEdit
        ? await authApi.setUserRole(account.id, role)
        : await authApi.createUser(username.trim(), password, role);
      onSaved(saved);
      toast.success(isEdit
        ? `${saved.username} is now ${ROLE_LABEL[saved.role].toLowerCase()}`
        : `Added ${saved.username}`);
      onClose();
    } catch (error) {

      toast.error(
        errorMessage(error, isEdit ? 'Could not change the role' : 'Could not create the account'),
        { title: 'Users' });
    } finally {
      setIsSaving(false);
    }
  };

  const heading = isEdit ? `Edit ${account.username}` : 'New account';

  const footer = (
    <>
      <button
        type="button"
        className={sectionStyles.outlineButton}
        onClick={onClose}
        disabled={isSaving}
      >
        Cancel
      </button>
      <button
        type="submit"
        form={`${uid}-form`}
        className={sectionStyles.saveButton}
        disabled={!canSubmit}
      >
        {isSaving
          ? (isEdit ? 'Saving…' : 'Creating…')
          : (isEdit ? 'Save changes' : 'Create account')}
      </button>
    </>
  );

  return (
    <Modal
      size="wide"
      label={heading}
      title={heading}
      description={isEdit
        ? 'What this account may do. It takes effect on their next request — they are not signed out.'
        : 'Someone else who can sign in to Affiche, and what they may do once they are in.'}
      isBusy={isSaving}
      onClose={onClose}
      footer={footer}
    >
      {
}
      <form id={`${uid}-form`} className={styles.body} onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor={`${uid}-username`}>Username</label>
          {isEdit ? (
            <span className={styles.readOnly}>{account.username}</span>
          ) : (
            <input
              id={`${uid}-username`}
              className={styles.input}
              type="text"
              autoComplete="off"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isSaving}
              autoFocus
            />
          )}
        </div>

        {!isEdit && (
          <div className={styles.field}>
            <label className={styles.label} htmlFor={`${uid}-password`}>Password</label>
            <input
              id={`${uid}-password`}
              className={styles.input}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSaving}
            />
          </div>
        )}

        {

}
        <fieldset className={styles.field}>
          <legend className={styles.label}>Role</legend>
          {ROLES.map((option) => (
            <label key={option} className={styles.option}>
              <input
                type="radio"
                className={styles.radio}
                name={`${uid}-role`}
                checked={role === option}
                disabled={isSaving}
                onChange={() => setRole(option)}
              />
              <span className={styles.optionText}>
                <span className={styles.optionName}>{ROLE_LABEL[option]}</span>
                <span className={sectionStyles.settingDescription}>{ROLE_SUMMARY[option]}</span>
              </span>
            </label>
          ))}
        </fieldset>
      </form>
    </Modal>
  );
}
