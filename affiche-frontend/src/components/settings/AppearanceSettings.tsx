import { useTheme } from '../../context/ThemeContext';
import type { ThemePreference } from '../../theme';
import sectionStyles from './SettingsSection.module.css';

const THEME_OPTIONS: { value: ThemePreference; label: string }[] = [
  { value: 'system', label: 'Match system' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
];

export function AppearanceSettings() {
  const { preference, resolved, setPreference } = useTheme();

  return (
    <section className={sectionStyles.section}>
      <h2 className={sectionStyles.sectionTitle}>Appearance</h2>
      <p className={sectionStyles.sectionDescription}>
        How Affiche looks in this browser.
      </p>

      <div className={sectionStyles.group}>
        <h3 className={sectionStyles.groupTitle}>Theme</h3>
        <p className={sectionStyles.groupDescription}>
          Saved on this device rather than on the server, so the same Affiche can be dark on one
          screen and light on another.
        </p>
        <div className={sectionStyles.row}>
          <div className={sectionStyles.rowStack}>
            <label className={sectionStyles.label} htmlFor="theme-preference">Theme</label>
            {preference === 'system' && (
              <p className={sectionStyles.rowDescription}>
                Following your system setting, which is currently {resolved}.
              </p>
            )}
          </div>
          <select
            id="theme-preference"
            className={sectionStyles.select}
            value={preference}
            onChange={(e) => setPreference(e.target.value as ThemePreference)}
          >
            {THEME_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
      </div>
    </section>
  );
}
