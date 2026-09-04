import { useState, useEffect, useRef } from 'react';
import { Eye, EyeOff, Save, CheckCircle, XCircle, Loader, Server, ChevronDown } from 'lucide-react';
import { LibraryTypeIcon, MediaServerIcon, Modal } from '../common';
import { errorMessage, mediaServerApi } from '../../api';
import type { MediaServerTestResult, MediaServerType } from '../../types';
import { SERVER_CONFIG } from './mediaServerHelpers';
import styles from './ConfigForm.module.css';
import modalStyles from '../common/Modal.module.css';
import sectionStyles from './SettingsSection.module.css';
import panelStyles from './AddMediaServerPanel.module.css';

const TEST_RESET_MS = 4000;

interface AddMediaServerPanelProps {
  onClose: () => void;
  onCreated: () => void;
}

export function AddMediaServerPanel({ onClose, onCreated }: AddMediaServerPanelProps) {

  const [serverType, setServerType] = useState<MediaServerType>('PLEX');
  const [url, setUrl] = useState(SERVER_CONFIG.PLEX.url);
  const [token, setToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [enabled, setEnabled] = useState(true);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [testResult, setTestResult] = useState<MediaServerTestResult | null>(null);
  const [selectedLibraries, setSelectedLibraries] = useState<Set<string>>(new Set());
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [testError, setTestError] = useState<string | null>(null);

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (testStatus !== 'error') return;
    const timer = setTimeout(() => setTestStatus('idle'), TEST_RESET_MS);
    return () => clearTimeout(timer);
  }, [testStatus]);

  const handleServerTypeChange = (newType: MediaServerType) => {
    setServerType(newType);
    setUrl(SERVER_CONFIG[newType].url);
    setIsDropdownOpen(false);
    setTestResult(null);
    setTestStatus('idle');
    setToken('');
  };

  const handleTestConnection = async () => {
    if (!url || !token) return;

    setTestStatus('testing');
    setTestError(null);
    setTestResult(null);
    setSelectedLibraries(new Set());

    try {
      const result = serverType === 'PLEX'
        ? await mediaServerApi.testPlex(url, token)
        : await mediaServerApi.testJellyfin(url, token);
      setTestResult(result);
      setSelectedLibraries(new Set(result.libraries.map(lib => lib.id)));
      setTestStatus('success');
    } catch (error) {
      setTestStatus('error');
      setTestError(errorMessage(error, 'Connection failed'));
    }
  };

  const handleLibraryToggle = (libraryId: string) => {
    setSelectedLibraries(prev => {
      const next = new Set(prev);
      if (next.has(libraryId)) {
        next.delete(libraryId);
      } else {
        next.add(libraryId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (testResult) {
      setSelectedLibraries(new Set(testResult.libraries.map(lib => lib.id)));
    }
  };

  const handleSelectNone = () => {
    setSelectedLibraries(new Set());
  };

  const handleSave = async () => {
    if (!testResult || selectedLibraries.size === 0) return;

    setIsSaving(true);
    setSaveError(null);

    try {
      const selectedLibraryObjects = testResult.libraries.filter(lib => selectedLibraries.has(lib.id));

      await mediaServerApi.create({
        name: testResult.name,
        type: serverType,
        url,
        token,
        enabled,
        libraries: selectedLibraryObjects,
      });

      onCreated();
    } catch (error) {
      setSaveError(errorMessage(error, 'Failed to save'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleUrlChange = (newUrl: string) => {
    setUrl(newUrl);
    setTestResult(null);
    setTestStatus('idle');
  };

  const handleTokenChange = (newToken: string) => {
    setToken(newToken);
    setTestResult(null);
    setTestStatus('idle');
  };

  const canSave = testStatus === 'success' && selectedLibraries.size > 0;

  return (

    <Modal
      size="drawer"
      label="Add media server"
      isBusy={isSaving}
      onClose={onClose}
      footer={
        <>
          {saveError && (
            <p className={`${modalStyles.footerNote} ${modalStyles.footerNoteError}`}>{saveError}</p>
          )}
          <button
            type="button"
            className={sectionStyles.outlineButton}
            onClick={onClose}
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            type="button"
            className={sectionStyles.saveButton}
            onClick={handleSave}
            disabled={isSaving || !canSave}
          >
            {isSaving ? <Loader size={16} className={styles.spinning} /> : <Save size={16} />}
            {isSaving ? 'Saving...' : 'Add Server'}
          </button>
        </>
      }
    >
      <div className={panelStyles.header}>
        <h3 className={styles.title}>Add Media Server</h3>
        <p className={styles.description}>Connect to your Plex or Jellyfin server</p>
      </div>

      <div className={panelStyles.content}>
        <div className={styles.field}>
          <label className={styles.label}>Server Type</label>
          <div ref={dropdownRef} className={panelStyles.dropdown}>
            <button
              type="button"
              className={panelStyles.dropdownTrigger}
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            >
              <span className={panelStyles.serverIcon}>
                <MediaServerIcon type={serverType} size={20} />
              </span>
              <span className={panelStyles.serverName}>{SERVER_CONFIG[serverType].name}</span>
              <ChevronDown
                size={18}
                className={`${panelStyles.dropdownChevron} ${isDropdownOpen ? panelStyles.dropdownChevronOpen : ''}`}
              />
            </button>

            {isDropdownOpen && (
              <div className={panelStyles.dropdownMenu}>
                {(Object.keys(SERVER_CONFIG) as MediaServerType[]).map((type) => (
                  <button
                    key={type}
                    type="button"
                    className={`${panelStyles.dropdownOption} ${serverType === type ? panelStyles.dropdownOptionSelected : ''}`}
                    onClick={() => handleServerTypeChange(type)}
                  >
                    <span className={panelStyles.serverIcon}>
                      <MediaServerIcon type={type} size={20} />
                    </span>
                    <span>{SERVER_CONFIG[type].name}</span>
                    {serverType === type && (

                      <CheckCircle
                        size={16}
                        className={panelStyles.selectedCheck}
                        style={{ color: SERVER_CONFIG[type].color }}
                      />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="server-url">Server URL</label>
          <input
            id="server-url"
            type="url"
            className={styles.input}
            value={url}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder={SERVER_CONFIG[serverType].url}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="server-token">
            {SERVER_CONFIG[serverType].tokenLabel}
          </label>
          <div className={styles.tokenWrapper}>
            <input
              id="server-token"
              type={showToken ? 'text' : 'password'}
              className={styles.input}
              value={token}
              onChange={(e) => handleTokenChange(e.target.value)}
              placeholder={SERVER_CONFIG[serverType].tokenPlaceholder}
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
        </div>

        <div className={styles.field}>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
            <span>Enabled</span>
          </label>
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className={`${sectionStyles.validateButton} ${testStatus === 'success' ? sectionStyles.validated : ''} ${testStatus === 'error' ? sectionStyles.failed : ''}`}
            onClick={handleTestConnection}
            disabled={!token || !url || testStatus === 'testing'}
          >
            {testStatus === 'testing' && <Loader size={16} className={styles.spinning} />}
            {testStatus === 'success' && <CheckCircle size={16} />}
            {testStatus === 'error' && <XCircle size={16} />}
            {testStatus === 'idle' && <Server size={16} />}
            {testStatus === 'testing' ? 'Testing...' :
             testStatus === 'success' ? 'Connected!' :
             testStatus === 'error' ? 'Failed' : 'Test Connection'}
          </button>
        </div>

        {testError && <p className={panelStyles.errorText}>{testError}</p>}

        {testResult && (
          <div className={panelStyles.libraryPicker}>
            <div className={panelStyles.libraryPickerHeader}>
              <div>
                <h4 className={panelStyles.libraryPickerTitle}>{testResult.name}</h4>
                <p className={panelStyles.libraryPickerHint}>
                  Select libraries to add ({selectedLibraries.size} of {testResult.libraries.length} selected)
                </p>
              </div>
              <div className={panelStyles.bulkActions}>
                <button type="button" className={panelStyles.bulkButton} onClick={handleSelectAll}>
                  Select All
                </button>
                <button
                  type="button"
                  className={`${panelStyles.bulkButton} ${panelStyles.bulkButtonMuted}`}
                  onClick={handleSelectNone}
                >
                  Select None
                </button>
              </div>
            </div>

            <div className={sectionStyles.cardList}>
              {testResult.libraries.map(library => (
                <label
                  key={library.id}
                  className={`${sectionStyles.card} ${panelStyles.libraryOption}`}
                >
                  <div className={sectionStyles.cardHeader}>
                    <input
                      type="checkbox"
                      className={panelStyles.libraryCheckbox}
                      checked={selectedLibraries.has(library.id)}
                      onChange={() => handleLibraryToggle(library.id)}
                    />
                    <div className={sectionStyles.cardIcon}><LibraryTypeIcon type={library.type} /></div>
                    <span className={sectionStyles.cardTitle}>{library.name}</span>
                    <span className={sectionStyles.cardCount}>{library.item_count} items</span>
                    <span className={panelStyles.libraryType}>{library.type}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
