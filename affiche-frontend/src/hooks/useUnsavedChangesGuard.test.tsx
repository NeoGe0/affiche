import { describe, expect, it } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider, useNavigate } from 'react-router-dom';

import { useUnsavedChangesGuard } from './useUnsavedChangesGuard';

function Editor({ dirty }: { dirty: boolean }) {
  const navigate = useNavigate();
  const guard = useUnsavedChangesGuard(dirty, (from, to) => from.pathname === to.pathname);
  return (
    <>
      <button onClick={() => navigate('/settings?section=fonts')}>Fonts</button>
      <button onClick={() => navigate('/dashboard')}>Dashboard</button>
      {guard.isAsking && (
        <>
          <p>Leave without saving?</p>
          <button onClick={guard.stay}>Keep editing</button>
          <button onClick={guard.leave}>Discard changes</button>
        </>
      )}
    </>
  );
}

function renderAt(dirty: boolean) {
  const router = createMemoryRouter(
    [
      { path: '/settings', element: <Editor dirty={dirty} /> },
      { path: '/dashboard', element: <p>Dashboard page</p> },
    ],
    { initialEntries: ['/settings'] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

const click = (name: string) => act(() => screen.getByRole('button', { name }).click());

describe('useUnsavedChangesGuard', () => {
  it('lets a clean editor go anywhere without asking', async () => {
    const router = renderAt(false);

    await click('Dashboard');

    expect(router.state.location.pathname).toBe('/dashboard');
  });

  it('asks before leaving with unsaved edits, and stays when told to', async () => {
    const router = renderAt(true);

    await click('Dashboard');
    expect(screen.getByText('Leave without saving?')).toBeInTheDocument();

    await click('Keep editing');
    expect(router.state.location.pathname).toBe('/settings');
    expect(screen.queryByText('Leave without saving?')).not.toBeInTheDocument();
  });

  it('leaves when the edits are discarded', async () => {
    const router = renderAt(true);

    await click('Dashboard');
    await click('Discard changes');

    expect(router.state.location.pathname).toBe('/dashboard');
  });

  it('does not ask for a move that keeps the editor mounted', async () => {
    const router = renderAt(true);

    await click('Fonts');

    expect(router.state.location.search).toBe('?section=fonts');
    expect(screen.queryByText('Leave without saving?')).not.toBeInTheDocument();
  });
});
