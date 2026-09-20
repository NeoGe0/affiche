import { Check, Circle } from 'lucide-react';

import type { PasswordRule } from './passwordRequirements';
import styles from './PasswordRules.module.css';

export function PasswordRules({ rules }: { rules: PasswordRule[] }) {
  return (
    <ul className={styles.rules} aria-label="Password requirements">
      {rules.map((rule) => (
        <li key={rule.label} className={rule.met ? styles.met : undefined}>
          {rule.met ? <Check size={14} aria-hidden="true" /> : <Circle size={14} aria-hidden="true" />}
          {rule.label}
          <span className="visually-hidden">{rule.met ? ' (met)' : ' (not met yet)'}</span>
        </li>
      ))}
    </ul>
  );
}
