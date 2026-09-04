import type { LibraryItem } from '../../types';
import type { LibraryRow } from '../../hooks/useLibraryRows';
import { ItemRow } from './ItemRow';
import styles from './LibraryRows.module.css';

interface LibraryRowsProps {
  rows: LibraryRow[];
  isLoading: boolean;
  onItemClick: (item: LibraryItem) => void;
  onOpenLibrary: (libraryId: number) => void;
}

const countLabel = (total: number) => `${total.toLocaleString()} item${total === 1 ? '' : 's'}`;

export function LibraryRows({
  rows, isLoading, onItemClick, onOpenLibrary,
}: LibraryRowsProps) {
  if (!isLoading && rows.length === 0) {
    return <p className={styles.empty}>This server has no libraries yet.</p>;
  }

  return (
    <div className={styles.rows}>
      {rows.map(({ library, items, total }) => (
        <ItemRow
          key={library.id}
          title={library.name}
          subtitle={countLabel(total)}
          items={items}
          isLoading={isLoading}
          onItemClick={onItemClick}
          onOpenAll={() => onOpenLibrary(library.id)}
          emptyLabel="This library holds no items yet."
        />
      ))}
    </div>
  );
}
