import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { NotificationsSettings } from './NotificationsSettings';
import { notificationsApi } from '../../api';
import type { NotificationTarget } from '../../types';

vi.mock('../../api', async () => {
  const actual = await vi.importActual<typeof import('../../api')>('../../api');
  return {
    ...actual,
    notificationsApi: {
      getTargets: vi.fn(),
      createTarget: vi.fn(),
      updateTarget: vi.fn(),
      deleteTarget: vi.fn(),
      testTarget: vi.fn(),
    },
  };
});

const toast = { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() };
vi.mock('../../context/ToastContext', () => ({ useToast: () => toast }));

const getTargets = vi.mocked(notificationsApi.getTargets);
const updateTarget = vi.mocked(notificationsApi.updateTarget);
const testTarget = vi.mocked(notificationsApi.testTarget);

const TARGET: NotificationTarget = {
  id: 1,
  name: 'Home Discord',
  type: 'discord',
  url_hint: 'discord.com',
  enabled: true,
  on_task_completed: true,
  on_task_failed: true,
  on_items_errored: false,
};

beforeEach(() => {
  vi.clearAllMocks();
  getTargets.mockResolvedValue([TARGET]);
  updateTarget.mockResolvedValue(TARGET);
});

describe('NotificationsSettings', () => {
  it('lists a target by name, service and host', async () => {
    render(<NotificationsSettings />);

    expect(await screen.findByText('Home Discord')).toBeInTheDocument();
    expect(screen.getByText(/Discord · discord\.com/)).toBeInTheDocument();
  });

  it('says which events a target actually hears about', async () => {

    render(<NotificationsSettings />);

    expect(await screen.findByText('on completed, failed')).toBeInTheDocument();
  });

  it('offers an empty state rather than a bare list', async () => {
    getTargets.mockResolvedValue([]);
    render(<NotificationsSettings />);

    expect(await screen.findByText(/No notification targets yet/)).toBeInTheDocument();
  });

  it('reports a target that refused the test without calling it an app error', async () => {

    testTarget.mockResolvedValue({ delivered: false });
    const user = userEvent.setup();
    render(<NotificationsSettings />);

    await user.click(await screen.findByRole('button', { name: /Send a test to Home Discord/ }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(toast.error.mock.calls[0][0]).toMatch(/did not accept/);
  });

  it('confirms a delivered test', async () => {
    testTarget.mockResolvedValue({ delivered: true });
    const user = userEvent.setup();
    render(<NotificationsSettings />);

    await user.click(await screen.findByRole('button', { name: /Send a test to Home Discord/ }));

    await waitFor(() => expect(toast.success).toHaveBeenCalled());
  });

  it('toggles a target without sending anything else', async () => {
    const user = userEvent.setup();
    render(<NotificationsSettings />);

    await user.click(await screen.findByRole('checkbox', { name: 'Enable Home Discord' }));

    await waitFor(() => expect(updateTarget).toHaveBeenCalledWith(1, { enabled: false }));
  });
});
