import type { TaskProgressState } from '../../types';

import styles from './TaskProgressBar.module.css';

interface TaskProgressBarProps {

  progress?: TaskProgressState | null;
}

export function TaskProgressBar({ progress }: TaskProgressBarProps) {
  if (!progress || progress.total <= 0) return null;
  const pct = Math.min(100, Math.round((progress.current / progress.total) * 100));

  return (
    <div className={styles.bar} role="progressbar"
         aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
      <div className={styles.fill} style={{ transform: `scaleX(${pct / 100})` }} />
    </div>
  );
}
