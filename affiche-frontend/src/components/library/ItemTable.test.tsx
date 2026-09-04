import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';

import { ItemTable } from './ItemTable';
import type { LibraryItem, SortState } from '../../types';

const item = (overrides: Partial<LibraryItem> = {}): LibraryItem => ({
  id: 7,
  library_id: 3,
  title: 'Arrival',
  type: 'movie',
  processed: true,
  locked: false,
  has_poster: false,
  ...overrides,
});

const SORT: SortState = { by: 'title', dir: 'asc' };

function renderTable(props: Partial<React.ComponentProps<typeof ItemTable>> = {}) {
  return render(
    <ItemTable
      items={[item()]}
      sort={SORT}
      onSortChange={vi.fn()}
      onItemClick={vi.fn()}
      {...props}
    />
  );
}

const titleButton = () => screen.getByRole('button', { name: 'Arrival' });
const header = (name: string | RegExp) => screen.getByRole('columnheader', { name });

describe('ItemTable rows', () => {
  it('opens an item from the keyboard, through a focusable control in the title cell', () => {
    const onItemClick = vi.fn();
    renderTable({ onItemClick });

    fireEvent.click(titleButton());

    expect(onItemClick).toHaveBeenCalledWith(expect.objectContaining({ title: 'Arrival' }));
  });

  it('opens the item once, not twice, when the control inside the row is used', () => {

    const onItemClick = vi.fn();
    renderTable({ onItemClick });

    fireEvent.click(titleButton());

    expect(onItemClick).toHaveBeenCalledTimes(1);
  });

  it('still opens the item when the row itself is clicked', () => {
    const onItemClick = vi.fn();
    renderTable({ onItemClick });

    fireEvent.click(screen.getByRole('row', { name: /Arrival/ }));

    expect(onItemClick).toHaveBeenCalledTimes(1);
  });

  it('selects instead of opening while select mode is on', () => {
    const onItemClick = vi.fn();
    const onToggleSelect = vi.fn();
    renderTable({
      onItemClick,
      onToggleSelect,
      onToggleSelectAll: vi.fn(),
      isSelected: () => false,
      selectMode: true,
    });

    fireEvent.click(titleButton());

    expect(onToggleSelect).toHaveBeenCalledTimes(1);
    expect(onItemClick).not.toHaveBeenCalled();
  });

  it('offers no control in the trash, where a row opens nothing', () => {
    renderTable({ variant: 'trash', onItemClick: undefined, onRestore: vi.fn() });

    expect(screen.queryByRole('button', { name: 'Arrival' })).toBeNull();

    expect(screen.getByText('Arrival')).toBeInTheDocument();
  });

  it('keeps the rows as rows', () => {

    renderTable();

    expect(screen.getAllByRole('row')).not.toHaveLength(0);
  });
});

describe('ItemTable sortable headers', () => {
  it('sorts from the keyboard, through a focusable control in the header cell', () => {
    const onSortChange = vi.fn();
    renderTable({ onSortChange });

    fireEvent.click(within(header(/Year/)).getByRole('button'));

    expect(onSortChange).toHaveBeenCalledWith({ by: 'year', dir: 'asc' });
  });

  it('toggles the direction of the column already sorted', () => {
    const onSortChange = vi.fn();
    renderTable({ onSortChange });

    fireEvent.click(within(header(/Title/)).getByRole('button'));

    expect(onSortChange).toHaveBeenCalledWith({ by: 'title', dir: 'desc' });
  });

  it('announces which column is sorted, and which way', () => {
    renderTable();

    expect(header(/Title/)).toHaveAttribute('aria-sort', 'ascending');
  });

  it('announces the other sortable columns as sortable but unsorted', () => {

    renderTable();

    expect(header(/Year/)).toHaveAttribute('aria-sort', 'none');
  });

  it('flips the announced direction with the sort', () => {
    renderTable({ sort: { by: 'title', dir: 'desc' } });

    expect(header(/Title/)).toHaveAttribute('aria-sort', 'descending');
  });

  it('keeps the headers as column headers', () => {
    renderTable();

    expect(screen.getAllByRole('columnheader').length).toBeGreaterThan(1);
  });
});
