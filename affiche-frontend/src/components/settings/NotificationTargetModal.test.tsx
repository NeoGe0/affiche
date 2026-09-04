import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { NotificationTargetModal } from './NotificationTargetModal';
import { notificationsApi } from '../../api';
import type { NotificationTarget } from '../../types';

vi.mock('../../api', async () => {
  const actual = await vi.importActual<typeof import('../../api')>('../../api');
  return {
    ...actual,
    notificationsApi: {
      createTarget: vi.fn(), updateTarget: vi.fn(), testUrl: vi.fn(), testTarget: vi.fn(),
    },
  };
});

vi.mock('../../context/ToastContext', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
}));

const createTarget = vi.mocked(notificationsApi.createTarget);
const updateTarget = vi.mocked(notificationsApi.updateTarget);
const testUrl = vi.mocked(notificationsApi.testUrl);
const testTarget = vi.mocked(notificationsApi.testTarget);

const TARGET: NotificationTarget = {
  id: 7,
  name: 'Home Discord',
  type: 'discord',
  url_hint: 'discord.com',
  enabled: true,
  on_task_completed: true,
  on_task_failed: true,
  on_items_errored: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  createTarget.mockResolvedValue(TARGET);
  updateTarget.mockResolvedValue(TARGET);
  testUrl.mockResolvedValue({ delivered: true });
  testTarget.mockResolvedValue({ delivered: true });
});

describe('NotificationTargetModal', () => {
  it('omits the URL from an edit that did not touch it', async () => {
    const user = userEvent.setup();
    render(
      <NotificationTargetModal target={TARGET} onSaved={vi.fn()} onClose={vi.fn()} />
    );

    await user.clear(screen.getByLabelText('Name'));
    await user.type(screen.getByLabelText('Name'), 'Renamed');
    await user.click(screen.getByRole('button', { name: 'Save target' }));

    await waitFor(() => expect(updateTarget).toHaveBeenCalled());
    expect(updateTarget.mock.calls[0][1]).not.toHaveProperty('url');
    expect(updateTarget.mock.calls[0][1].name).toBe('Renamed');
  });

  it('sends the URL when the edit does replace it', async () => {
    const user = userEvent.setup();
    render(
      <NotificationTargetModal target={TARGET} onSaved={vi.fn()} onClose={vi.fn()} />
    );

    await user.type(screen.getByLabelText('URL'), 'https://discord.com/api/webhooks/2/new');
    await user.click(screen.getByRole('button', { name: 'Save target' }));

    await waitFor(() => expect(updateTarget).toHaveBeenCalled());
    expect(updateTarget.mock.calls[0][1].url).toBe('https://discord.com/api/webhooks/2/new');
  });

  it('shows the stored host as a placeholder, never the URL itself', () => {
    render(<NotificationTargetModal target={TARGET} onSaved={vi.fn()} onClose={vi.fn()} />);

    const url = screen.getByLabelText('URL');
    expect(url).toHaveValue('');
    expect(url).toHaveAttribute('placeholder', expect.stringContaining('discord.com'));
  });

  it('cannot create a target without a URL', async () => {
    const user = userEvent.setup();
    render(<NotificationTargetModal onSaved={vi.fn()} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Name'), 'New one');

    expect(screen.getByRole('button', { name: 'Create target' })).toBeDisabled();
  });

  it('creates a target with the events that were ticked', async () => {
    const user = userEvent.setup();
    render(<NotificationTargetModal onSaved={vi.fn()} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Name'), 'New one');
    await user.type(screen.getByLabelText('URL'), 'https://gotify/message?token=x');
    await user.click(screen.getByRole('checkbox', { name: 'A run fails' }));
    await user.click(screen.getByRole('button', { name: 'Create target' }));

    await waitFor(() => expect(createTarget).toHaveBeenCalled());
    expect(createTarget.mock.calls[0][0]).toMatchObject({
      name: 'New one',
      url: 'https://gotify/message?token=x',
      on_task_completed: true,
      on_task_failed: false,
    });
  });
});

describe('NotificationTargetModal test button', () => {
  const testButton = () => screen.getByRole('button', { name: /Send a test|Sending|Delivered|Not delivered/ });

  it('tries the URL in the form, which is not stored anywhere yet', async () => {
    const user = userEvent.setup();
    render(<NotificationTargetModal onSaved={vi.fn()} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Name'), 'New one');
    await user.type(screen.getByLabelText('URL'), 'https://discord.com/api/webhooks/1/abc');
    await user.click(testButton());

    await waitFor(() => expect(testUrl).toHaveBeenCalledWith({
      type: 'discord', url: 'https://discord.com/api/webhooks/1/abc', name: 'New one',
    }));

    expect(createTarget).not.toHaveBeenCalled();
  });

  it('tries the stored target when an edit leaves the URL field alone', async () => {
    const user = userEvent.setup();
    render(<NotificationTargetModal target={TARGET} onSaved={vi.fn()} onClose={vi.fn()} />);

    await user.click(testButton());

    await waitFor(() => expect(testTarget).toHaveBeenCalledWith(7));
    expect(testUrl).not.toHaveBeenCalled();
  });

  it('still saves after a test that did not arrive', async () => {
    testUrl.mockResolvedValue({ delivered: false });
    const user = userEvent.setup();
    render(<NotificationTargetModal onSaved={vi.fn()} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Name'), 'New one');
    await user.type(screen.getByLabelText('URL'), 'https://discord.com/api/webhooks/1/abc');
    await user.click(testButton());
    await screen.findByRole('button', { name: /Not delivered/ });

    const save = screen.getByRole('button', { name: 'Create target' });
    expect(save).toBeEnabled();
    await user.click(save);

    await waitFor(() => expect(createTarget).toHaveBeenCalled());
  });

  it('drops a stale answer when the fields it was about change', async () => {
    const user = userEvent.setup();
    render(<NotificationTargetModal onSaved={vi.fn()} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('URL'), 'https://discord.com/api/webhooks/1/abc');
    await user.click(testButton());
    await screen.findByRole('button', { name: /Delivered/ });

    await user.type(screen.getByLabelText('URL'), '-changed');

    expect(screen.getByRole('button', { name: /Send a test/ })).toBeInTheDocument();
  });

  it('has nothing to try on a new target with no URL yet', async () => {
    render(<NotificationTargetModal onSaved={vi.fn()} onClose={vi.fn()} />);

    expect(testButton()).toBeDisabled();
  });
});
