import { Settings } from 'lucide-react';

import { PosterPreview } from '../image';
import type { OverlayOptions, TextOptions } from '../../types';
import styles from './PosterPreviewPane.module.css';

interface PosterPreviewPaneProps {

  imageUrl: string | null;
  title: string;

  overlayOptions?: OverlayOptions;
  textOptions?: TextOptions;
  onEditStyle: () => void;
}

export function PosterPreviewPane({
  imageUrl,
  title,
  overlayOptions,
  textOptions,
  onEditStyle,
}: PosterPreviewPaneProps) {
  return (
    <div className={styles.section}>
      <h3 className={styles.title}>Preview</h3>
      {imageUrl && overlayOptions && textOptions ? (
        <>
          <PosterPreview
            imageUrl={imageUrl}
            title={title}
            overlayOptions={overlayOptions}
            textOptions={textOptions}
          />
          <button className={styles.editButton} onClick={onEditStyle}>
            <Settings size={16} />
            Edit Style
          </button>
        </>
      ) : (
        <div className={styles.placeholder}>Select a poster to see preview</div>
      )}
    </div>
  );
}
