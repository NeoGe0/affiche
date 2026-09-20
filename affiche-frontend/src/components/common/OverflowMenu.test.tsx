import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { OverflowMenu } from './OverflowMenu';

function renderMenu() {
  const onSync = vi.fn();
  render(
    <OverflowMenu
      title="Library actions"
      items={[
        { label: 'Sync library', onClick: onSync },
        { label: 'Upload posters', onClick: vi.fn(), disabled: true },
        { label: 'Reset posters', onClick: vi.fn(), danger: true },
      ]}
    />
  );
  return { onSync };
}

describe('OverflowMenu keyboard', () => {
  it('moves focus into the menu when it opens, and between items with the arrow keys', async () => {
    const user = userEvent.setup();
    renderMenu();

    await user.click(screen.getByRole('button', { name: 'Library actions' }));
    expect(screen.getByRole('menuitem', { name: 'Sync library' })).toHaveFocus();

    await user.keyboard('{ArrowDown}');

    expect(screen.getByRole('menuitem', { name: 'Reset posters' })).toHaveFocus();

    await user.keyboard('{Home}');
    expect(screen.getByRole('menuitem', { name: 'Sync library' })).toHaveFocus();
  });

  it('closes on Escape with focus back on the trigger', async () => {
    const user = userEvent.setup();
    renderMenu();
    const trigger = screen.getByRole('button', { name: 'Library actions' });

    await user.click(trigger);
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
