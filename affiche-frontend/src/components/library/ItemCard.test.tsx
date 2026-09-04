import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { ItemCard } from './ItemCard';
import type { LibraryItem } from '../../types';
import { markCached, resetCachedImages } from '../../test/cachedImage';

afterEach(resetCachedImages);

function makeItem(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    id: 7,
    library_id: 3,
    title: 'Arrival',
    type: 'movie',
    processed: true,
    locked: false,
    has_poster: true,
    ...overrides,
  };
}

const renderCard = (item: LibraryItem) =>
  render(<ItemCard item={item} onClick={() => {}} />);

const placeholder = () => screen.queryByText('A');
const poster = () => screen.queryByRole('img');

const lockButton = () => screen.getByRole('button', { name: /lock/i });

describe('ItemCard poster', () => {
  it('shows the letter placeholder until the poster loads', () => {
    renderCard(makeItem());

    expect(placeholder()).toBeInTheDocument();
    expect(poster()).toBeInTheDocument();
  });

  it('hides the placeholder once the poster fires load', () => {
    renderCard(makeItem());

    fireEvent.load(poster()!);

    expect(placeholder()).not.toBeInTheDocument();
  });

  it('hides the placeholder for an already-cached poster that never fires load', () => {

    markCached('/libraries/3/items/7/poster');

    renderCard(makeItem());

    expect(placeholder()).not.toBeInTheDocument();
  });

  it('falls back to the placeholder when the poster errors', () => {
    renderCard(makeItem());

    fireEvent.error(poster()!);

    expect(placeholder()).toBeInTheDocument();
    expect(poster()).not.toBeInTheDocument();
  });

  it('retries after an error when a new poster version arrives', () => {

    const { rerender } = renderCard(makeItem());
    fireEvent.error(poster()!);
    expect(poster()).not.toBeInTheDocument();

    rerender(
      <ItemCard item={makeItem({ poster_version: 'b2c-1f' })} onClick={() => {}} />
    );

    const retried = poster();
    expect(retried).toBeInTheDocument();
    expect(retried).toHaveAttribute('src', expect.stringContaining('v=b2c-1f') as unknown as string);
  });

  it('does not carry a previous poster loaded state onto a new version', () => {

    const { rerender } = renderCard(makeItem());
    fireEvent.load(poster()!);
    expect(placeholder()).not.toBeInTheDocument();

    rerender(
      <ItemCard item={makeItem({ poster_version: 'c3d-20' })} onClick={() => {}} />
    );

    expect(placeholder()).toBeInTheDocument();
  });

  it('requests the grid thumbnail, not the full-resolution poster', () => {

    renderCard(makeItem({ poster_version: 'b2c-1f' }));

    expect(poster()?.getAttribute('src')).toContain('size=thumb');
  });

  it('does not request a poster when none exists', () => {
    renderCard(makeItem({ has_poster: false, poster_version: undefined }));

    expect(poster()).not.toBeInTheDocument();
    expect(placeholder()).toBeInTheDocument();
  });
});

describe('ItemCard select mode', () => {

  const card = () => screen.getByRole('button');

  it('opens the item on click when select mode is off', () => {
    const onClick = vi.fn();
    const onToggleSelect = vi.fn();
    render(
      <ItemCard item={makeItem()} onClick={onClick} onToggleSelect={onToggleSelect} />
    );

    fireEvent.click(card());

    expect(onClick).toHaveBeenCalledOnce();
    expect(onToggleSelect).not.toHaveBeenCalled();
  });

  it('selects instead of opening when select mode is on', () => {
    const onClick = vi.fn();
    const onToggleSelect = vi.fn();
    render(
      <ItemCard item={makeItem()} onClick={onClick} onToggleSelect={onToggleSelect} selectMode />
    );

    fireEvent.click(card());

    expect(onToggleSelect).toHaveBeenCalledOnce();
    expect(onClick).not.toHaveBeenCalled();
  });

  it('still opens in select mode where selection is not offered', () => {

    const onClick = vi.fn();
    render(<ItemCard item={makeItem()} onClick={onClick} selectMode />);

    fireEvent.click(card());

    expect(onClick).toHaveBeenCalledOnce();
  });

  it('reports selected state to assistive tech in select mode', () => {
    render(
      <ItemCard item={makeItem()} onClick={() => {}} onToggleSelect={() => {}} selectMode isSelected />
    );

    expect(card()).toHaveAttribute('aria-pressed', 'true');
  });

  it('leaves the card unpressed when it is merely openable', () => {

    render(<ItemCard item={makeItem()} onClick={() => {}} onToggleSelect={() => {}} />);

    expect(card()).not.toHaveAttribute('aria-pressed');
  });
});

describe('ItemCard badges', () => {
  it('marks a failed item', () => {
    renderCard(makeItem({ error_message: 'No poster found' }));

    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('shows the failure alongside the lock control', () => {

    render(
      <ItemCard
        item={makeItem({ locked: true, error_message: 'No poster found' })}
        onClick={() => {}}
        onToggleLock={() => {}}
      />
    );

    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(lockButton()).toHaveAttribute('aria-pressed', 'true');
  });

  it('shows no lock control in the trash view, where locking means nothing', () => {
    render(
      <ItemCard item={makeItem({ locked: true })} variant="trash" onToggleLock={() => {}} />
    );

    expect(screen.queryByRole('button', { name: /lock/i })).not.toBeInTheDocument();
  });
});

describe('ItemCard lock', () => {

  it('toggles the lock without opening the item', () => {
    const onClick = vi.fn();
    const onToggleLock = vi.fn();
    render(
      <ItemCard item={makeItem()} onClick={onClick} onToggleLock={onToggleLock} />
    );

    fireEvent.click(lockButton());

    expect(onToggleLock).toHaveBeenCalledOnce();

    expect(onClick).not.toHaveBeenCalled();
  });

  it('reports an unlocked item as unpressed', () => {
    render(<ItemCard item={makeItem()} onClick={() => {}} onToggleLock={() => {}} />);

    expect(lockButton()).toHaveAttribute('aria-pressed', 'false');
  });

  it('hides the lock in select mode, where the selection bar owns locking', () => {
    render(
      <ItemCard
        item={makeItem()}
        onClick={() => {}}
        onToggleSelect={() => {}}
        onToggleLock={() => {}}
        selectMode
      />
    );

    expect(screen.queryByRole('button', { name: /lock/i })).not.toBeInTheDocument();
  });

  it('refuses a second click while the first is in flight', () => {
    const onToggleLock = vi.fn();
    render(
      <ItemCard
        item={makeItem()}
        onClick={() => {}}
        onToggleLock={onToggleLock}
        isLockPending
      />
    );

    fireEvent.click(lockButton());

    expect(onToggleLock).not.toHaveBeenCalled();
  });
});
