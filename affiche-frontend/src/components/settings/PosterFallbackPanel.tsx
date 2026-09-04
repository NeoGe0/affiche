import { ImageOff } from 'lucide-react';

import sectionStyles from './SettingsSection.module.css';
import styles from './PosterFallbackPanel.module.css';

interface PosterFallbackPanelProps {

  fallbackToServerPoster: boolean;

  skipStyleWhenNotTextless: boolean;
  isSaving: boolean;
  onChange: (patch: {
    fallback_to_server_poster?: boolean;
    skip_style_when_not_textless?: boolean;
  }) => void;
}

export function PosterFallbackPanel({
  fallbackToServerPoster,
  skipStyleWhenNotTextless,
  isSaving,
  onChange,
}: PosterFallbackPanelProps) {
  return (
    <div className={sectionStyles.divider}>
      <div className={styles.header}>
        <ImageOff size={16} className={styles.icon} />
        <span className={styles.title}>Poster fallbacks</span>
      </div>
      <p className={styles.description}>
        What to do when the languages above don&apos;t produce a poster, and when the one they do
        produce already has a title printed on it.
      </p>

      <label className={`${sectionStyles.toggle} ${styles.toggle}`}>
        <input
          type="checkbox"
          checked={fallbackToServerPoster}
          disabled={isSaving}
          onChange={(e) => onChange({ fallback_to_server_poster: e.target.checked })}
        />
        <span>Style the media server&apos;s own poster</span>
      </label>
      <p className={styles.hint}>
        When no provider has artwork in any language, apply your styles to the poster the item
        already has instead of leaving the item unprocessed.
      </p>

      <label className={`${sectionStyles.toggle} ${styles.toggle}`}>
        <input
          type="checkbox"
          checked={skipStyleWhenNotTextless}
          disabled={isSaving}
          onChange={(e) => onChange({ skip_style_when_not_textless: e.target.checked })}
        />
        <span>Use posters that already have a title as-is</span>
      </label>
      <p className={styles.hint}>
        Falling back past the textless entry gives a poster with its own title. Upload it
        undecorated rather than printing a second title over the first.
      </p>
    </div>
  );
}
