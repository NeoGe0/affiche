import type { ReactNode } from 'react';
import { Check } from 'lucide-react';

import type { StepState } from './welcomeSteps';
import styles from './Welcome.module.css';

interface SetupStepProps {
  number: number;
  title: string;

  summary: string;
  state: StepState;

  onChange?: () => void;

  children: ReactNode;
}

export function SetupStep({ number, title, summary, state, onChange, children }: SetupStepProps) {
  const headingId = `setup-step-${number}`;
  return (
    <li className={`${styles.step} ${styles[state]}`} aria-current={state === 'current' ? 'step' : undefined}>
      <div className={styles.stepHead}>
        <span className={styles.stepNumber} aria-hidden="true">
          {state === 'done' ? <Check size={16} /> : number}
        </span>
        <div className={styles.stepText}>
          <h3 className={styles.stepTitle} id={headingId}>
            {title}
            {state === 'done' && <span className="visually-hidden"> (done)</span>}
          </h3>
          <p className={styles.stepSummary}>{summary}</p>
        </div>
        {state === 'done' && onChange && (
          <button type="button" className={styles.linkButton} onClick={onChange} aria-describedby={headingId}>
            Change
          </button>
        )}
      </div>
      {state === 'current' && <div className={styles.stepBody}>{children}</div>}
    </li>
  );
}
