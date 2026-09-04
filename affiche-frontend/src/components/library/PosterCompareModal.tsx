import { Modal } from '../common';
import { PosterCompareSlider } from '../image';
import styles from './PosterCompareModal.module.css';

interface PosterCompareModalProps {

  title: string;
  beforeUrl: string;
  afterUrl: string;
  onClose: () => void;
}

export function PosterCompareModal({ title, beforeUrl, afterUrl, onClose }: PosterCompareModalProps) {
  return (
    <Modal size="large" label={`Compare posters — ${title}`} onClose={onClose}>
      <div className={styles.header}>
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.hint}>Drag the handle to compare the original with the generated poster.</p>
      </div>
      <div className={styles.body}>
        <div className={styles.frame}>
          <PosterCompareSlider
            beforeUrl={beforeUrl}
            afterUrl={afterUrl}
            alt={title}
            placeholder={<span>{title.charAt(0)}</span>}
          />
        </div>
      </div>
    </Modal>
  );
}
