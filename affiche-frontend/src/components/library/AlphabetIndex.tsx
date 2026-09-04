import type { AlphaIndexEntry } from '../../types';
import styles from './AlphabetIndex.module.css';

const LETTERS = ['#', ...Array.from({ length: 26 }, (_, i) => String.fromCharCode(65 + i))];

interface AlphabetIndexProps {
  entries: AlphaIndexEntry[];
  onLetterClick: (letter: string) => void;
}

export function AlphabetIndex({ entries, onLetterClick }: AlphabetIndexProps) {
  const available = new Set(entries.map((e) => e.letter));

  return (
    <nav className={styles.rail} aria-label="Jump to letter">
      {LETTERS.map((letter) => {
        const enabled = available.has(letter);
        return (
          <button
            key={letter}
            type="button"
            className={styles.letter}
            disabled={!enabled}
            onClick={() => enabled && onLetterClick(letter)}
          >
            {letter}
          </button>
        );
      })}
    </nav>
  );
}
