import type { ItemStats } from '../../types';
import { coverageLine, coveragePercent, failedPercent } from './coverage';
import styles from './CoverageMeter.module.css';

interface CoverageMeterProps {

  label: string;
  stats: ItemStats;

  variant?: 'row' | 'stage';
}

export function CoverageMeter({ label, stats, variant = 'row' }: CoverageMeterProps) {
  const percent = coveragePercent(stats);
  const line = coverageLine(stats);
  return (
    <div className={`${styles.meter} ${styles[variant]}`}>
      <span className={styles.percent}>{percent}%</span>
      <span className={styles.bar} role="img" aria-label={`${label}: ${line}`}>
        <span className={styles.done} style={{ width: `${percent}%` }} />
        {stats.errors > 0 && (
          <span className={styles.failed} style={{ width: `${Math.max(1, failedPercent(stats))}%` }} />
        )}
      </span>
      <span className={styles.line} aria-hidden="true">{line}</span>
    </div>
  );
}
