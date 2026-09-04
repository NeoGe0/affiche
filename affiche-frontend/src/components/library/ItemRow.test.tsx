import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { ItemRow } from './ItemRow';
import type { LibraryItem } from '../../types';

const item = (id: number): LibraryItem =>
  ({ id, library_id: 1, title: `Item ${id}`, type: 'movie', processed: false, locked: false });

const items = Array.from({ length: 10 }, (_, i) => item(i));

function withWidths(scrollWidth: number, clientWidth: number) {
  for (const [name, value] of [['scrollWidth', scrollWidth], ['clientWidth', clientWidth]] as const) {
    Object.defineProperty(HTMLElement.prototype, name, { value, configurable: true });
  }
}

const renderRow = (props: Partial<React.ComponentProps<typeof ItemRow>> = {}) => {
  const onItemClick = vi.fn();
  render(<ItemRow title="Films" items={items} onItemClick={onItemClick} {...props} />);
  return onItemClick;
};

afterEach(() => withWidths(0, 0));

describe('ItemRow', () => {
  it('offers a live right arrow while there is more strip to reach', () => {
    withWidths(2000, 800);
    const scrollBy = vi.fn();
    HTMLElement.prototype.scrollBy = scrollBy;
    renderRow();

    expect(screen.getByRole('button', { name: /scroll films left/i })).toBeDisabled();
    const right = screen.getByRole('button', { name: /scroll films right/i });
    expect(right).toBeEnabled();

    fireEvent.click(right);

    expect(scrollBy).toHaveBeenCalledWith(expect.objectContaining({ left: expect.any(Number) }));
    expect(scrollBy.mock.calls[0][0].left).toBeGreaterThan(0);
  });

  it('leaves both arrows dead when every card already fits', () => {
    withWidths(800, 800);
    renderRow();

    expect(screen.getByRole('button', { name: /scroll films left/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /scroll films right/i })).toBeDisabled();
  });

  it('offers no arrows at all for a row with nothing in it', () => {
    withWidths(2000, 800);
    renderRow({ items: [] });

    expect(screen.queryByRole('button', { name: /scroll/i })).not.toBeInTheDocument();
  });

  it('opens the item a card stands for', () => {
    withWidths(2000, 800);
    const onItemClick = renderRow();

    fireEvent.click(screen.getByText('Item 3'));

    expect(onItemClick).toHaveBeenCalledWith(items[3]);
  });
});
