import { useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { LibraryItem } from '../../types';
import { ItemCard } from './ItemCard';
import styles from './ItemRow.module.css';

const CARD_STRIDE = 180;

interface ItemRowProps {
  title: string;

  subtitle?: string;
  items: LibraryItem[];
  onItemClick: (item: LibraryItem) => void;

  onOpenAll?: () => void;

  isLoading?: boolean;
  emptyLabel?: string;
}

export function ItemRow({
  title, subtitle, items, onItemClick, onOpenAll, isLoading = false,
  emptyLabel = 'Nothing here yet.',
}: ItemRowProps) {
  const track = useRef<HTMLDivElement>(null);

  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(true);

  const readEdges = (el: HTMLDivElement) => {
    setAtStart(el.scrollLeft <= 1);

    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 1);
  };

  const scrollByPage = (direction: -1 | 1) => {
    const el = track.current;
    if (!el) return;
    const page = Math.max(el.clientWidth - CARD_STRIDE, CARD_STRIDE);
    el.scrollBy({ left: direction * page, behavior: 'smooth' });
  };

  const heading = (
    <>
      <span className={styles.title}>{title}</span>
      {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
    </>
  );

  return (
    <section className={styles.row}>
      <div className={styles.header}>
        {onOpenAll ? (
          <button type="button" className={styles.headingButton} onClick={onOpenAll}>
            {heading}
            <ChevronRight size={16} className={styles.chevron} />
          </button>
        ) : (
          <div className={styles.heading}>{heading}</div>
        )}
        {items.length > 0 && !isLoading && (
          <div className={styles.arrows}>
            <button
              type="button"
              className={styles.arrow}
              onClick={() => scrollByPage(-1)}
              disabled={atStart}
              aria-label={`Scroll ${title} left`}
            >
              <ChevronLeft size={16} />
            </button>
            <button
              type="button"
              className={styles.arrow}
              onClick={() => scrollByPage(1)}
              disabled={atEnd}
              aria-label={`Scroll ${title} right`}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>

      {isLoading ? (

        <div className={styles.track}>
          {Array.from({ length: 6 }, (_, i) => <div key={i} className={styles.placeholder} />)}
        </div>
      ) : items.length === 0 ? (
        <p className={styles.empty}>{emptyLabel}</p>
      ) : (
        <div
          className={styles.track}
          ref={(el) => {
            track.current = el;

            if (el) readEdges(el);
          }}
          onScroll={(e) => readEdges(e.currentTarget)}
        >
          {items.map((item) => (
            <div key={`${item.library_id}-${item.id}`} className={styles.cell}>
              <ItemCard item={item} onClick={() => onItemClick(item)} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
