import { useEffect, useState } from 'react';
import { Eye, EyeOff, Save, CheckCircle, XCircle, Loader, ExternalLink } from 'lucide-react';
import sectionStyles from './SettingsSection.module.css';
import styles from './ConfigForm.module.css';

interface ConfigFormProps {
  title: string;
  description?: string;
  serviceName: string;
  serviceType: 'LIBRARY' | 'PROVIDER';
  initialUrl?: string;

  hasStoredToken?: boolean;

  storedTokenHint?: string | null;
  initialEnabled?: boolean;
  showUrl?: boolean;
  readOnlyUrl?: boolean;
  hideHeader?: boolean;
  hideToken?: boolean;
  getKeyUrl?: string;

  onSave: (data: { url: string; token?: string; enabled: boolean }) => void;
  onValidate?: (url: string, token: string) => Promise<boolean>;
  isSaving?: boolean;

  formId?: string;
  onSubmittableChange?: (submittable: boolean) => void;
}

export function ConfigForm({
  title,
  description,
  serviceName,
  initialUrl = '',
  hasStoredToken = false,
  storedTokenHint = null,
  initialEnabled = true,
  showUrl = true,
  readOnlyUrl = false,
  hideHeader = false,
  hideToken = false,
  getKeyUrl,
  onSave,
  onValidate,
  isSaving,
  formId,
  onSubmittableChange,
}: ConfigFormProps) {
  const [url, setUrl] = useState(initialUrl);

  const [token, setToken] = useState('');
  const [enabled, setEnabled] = useState(initialEnabled);
  const [showToken, setShowToken] = useState(false);
  const [validateStatus, setValidateStatus] = useState<'idle' | 'validating' | 'success' | 'error'>('idle');

  const [isValidated, setIsValidated] = useState(hasStoredToken);

  const [hasChanges, setHasChanges] = useState(false);

  const [isEditingToken, setIsEditingToken] = useState(!hasStoredToken);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    onSave({ url, enabled, ...(token ? { token } : {}) });
  };

  const handleUrlChange = (newUrl: string) => {
    setUrl(newUrl);
    setHasChanges(true);
    setIsValidated(false);
    setValidateStatus('idle');
  };

  const handleTokenChange = (newToken: string) => {
    setToken(newToken);
    setHasChanges(true);
    setIsValidated(false);
    setValidateStatus('idle');
  };

  const handleChangeToken = () => {
    setIsEditingToken(true);
    setShowToken(false);
    handleTokenChange('');
  };

  const canValidate = !!onValidate && (!!token || hideToken);

  const handleValidate = async () => {
    if (!canValidate) return;
    setValidateStatus('validating');
    try {
      const success = await onValidate(url, token);
      setValidateStatus(success ? 'success' : 'error');
      setIsValidated(success);
      if (!success) {
        setTimeout(() => setValidateStatus('idle'), 4000);
      }
    } catch {
      setValidateStatus('error');
      setIsValidated(false);
      setTimeout(() => setValidateStatus('idle'), 4000);
    }
  };

  const canSave = !onValidate || isValidated || !hasChanges;

  useEffect(() => {
    onSubmittableChange?.(canSave);
  }, [canSave, onSubmittableChange]);

  return (
    <form id={formId} className={styles.form} onSubmit={handleSubmit}>
      {!hideHeader && (
        <div className={styles.header}>
          <h3 className={styles.title}>{title}</h3>
          {description && <p className={styles.description}>{description}</p>}
        </div>
      )}

      {showUrl && (
        <div className={styles.field}>
          <label className={styles.label} htmlFor={`${serviceName}-url`}>
            API URL
          </label>
          <input
            id={`${serviceName}-url`}
            type="url"
            className={`${styles.input} ${readOnlyUrl ? styles.readOnly : ''}`}
            value={url}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder="https://api.example.com"
            readOnly={readOnlyUrl}
            disabled={readOnlyUrl}

            required={!readOnlyUrl}
          />
          {readOnlyUrl && (
            <span className={styles.hint}>URL is managed by the backend</span>
          )}
        </div>
      )}

      {!hideToken && (
      <div className={styles.field}>
        <div className={styles.labelRow}>
          <label className={styles.label} htmlFor={`${serviceName}-token`}>
            API Token
          </label>
          {getKeyUrl && (
            <a
              className={styles.getKeyLink}
              href={getKeyUrl}
              target="_blank"
              rel="noreferrer noopener"
            >
              Get your API key
              <ExternalLink size={12} />
            </a>
          )}
        </div>
        {isEditingToken ? (
          <div className={styles.tokenWrapper}>
            <input
              id={`${serviceName}-token`}
              type={showToken ? 'text' : 'password'}
              className={styles.input}
              value={token}
              onChange={(e) => handleTokenChange(e.target.value)}
              placeholder="Enter API token"
              required
            />
            <button
              type="button"
              className={styles.toggleToken}
              onClick={() => setShowToken(!showToken)}
            >
              {showToken ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        ) : (
          <div className={styles.maskedToken}>
            <span className={styles.maskedValue}>
              {storedTokenHint ? `••••••••••${storedTokenHint}` : '•••••••••••••• configured'}
            </span>
            <button type="button" className={styles.changeTokenButton} onClick={handleChangeToken}>
              Change token
            </button>
          </div>
        )}
      </div>
      )}

      <div className={styles.field}>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          <span>Enabled</span>
        </label>
      </div>

      <div className={styles.actions}>
        {onValidate && (
          <button
            type="button"
            className={`${sectionStyles.validateButton} ${validateStatus === 'success' ? sectionStyles.validated : ''} ${validateStatus === 'error' ? sectionStyles.failed : ''}`}
            onClick={handleValidate}
            disabled={!canValidate || validateStatus === 'validating'}
          >
            {validateStatus === 'validating' && <Loader size={16} className={styles.spinning} />}
            {validateStatus === 'success' && <CheckCircle size={16} />}
            {validateStatus === 'error' && <XCircle size={16} />}
            {validateStatus === 'idle' && <CheckCircle size={16} />}
            {validateStatus === 'validating' ? 'Validating...' :
             validateStatus === 'success' ? 'Valid!' :
             validateStatus === 'error' ? 'Invalid' : 'Validate'}
          </button>
        )}
        {!formId && (
          <button
            type="submit"
            className={styles.saveButton}
            disabled={isSaving || !canSave}
            title={!canSave ? 'Validate credentials first' : undefined}
          >
            <Save size={16} />
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        )}
      </div>
    </form>
  );
}
