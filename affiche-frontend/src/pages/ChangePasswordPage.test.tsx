import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ChangePasswordPage } from './ChangePasswordPage';
import { AuthProvider } from '../context/AuthContext';
import { authApi } from '../api';

vi.mock('../api', () => ({
  authApi: {
    status: vi.fn(),
    login: vi.fn(),
    setup: vi.fn(),
    logout: vi.fn(),
    me: vi.fn(),
    changePassword: vi.fn(),
  },

  errorMessage: (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback,
}));

const status = vi.mocked(authApi.status);
const changePassword = vi.mocked(authApi.changePassword);

const TEMPORARY = 'printed-in-the-log';
const CHOSEN = 'one-i-picked-myself';

beforeEach(() => {
  vi.resetAllMocks();
  status.mockResolvedValue({
    setup_required: false,
    authenticated: true,
    username: 'admin',
    password_change_required: true,
  });
});

const renderPage = () =>
  render(
    <AuthProvider>
      <ChangePasswordPage />
    </AuthProvider>
  );

const fill = async (
  user: ReturnType<typeof userEvent.setup>,
  { current = TEMPORARY, next = CHOSEN, confirm = CHOSEN } = {}
) => {
  await user.type(screen.getByLabelText('Temporary password'), current);
  await user.type(screen.getByLabelText('New password'), next);
  await user.type(screen.getByLabelText('Confirm new password'), confirm);
  await user.click(screen.getByRole('button', { name: 'Set password' }));
};

describe('ChangePasswordPage', () => {
  it('says why it is being shown, so the temporary password is not mistaken for the real one', async () => {
    renderPage();

    expect(await screen.findByText(/written to the server log/)).toBeInTheDocument();
  });

  it('sends the temporary password along with the chosen one', async () => {
    changePassword.mockResolvedValue({ username: 'admin', role: 'ADMIN', password_change_required: false });
    const user = userEvent.setup();
    renderPage();

    await fill(user);

    await waitFor(() => expect(changePassword).toHaveBeenCalledWith(TEMPORARY, CHOSEN));
  });

  it('refuses a mistyped confirmation without asking the backend', async () => {
    const user = userEvent.setup();
    renderPage();

    await fill(user, { confirm: 'something-else' });

    expect(await screen.findByText('Passwords do not match')).toBeInTheDocument();
    expect(changePassword).not.toHaveBeenCalled();
  });

  it('surfaces the reason the backend gave and stays on the form', async () => {
    changePassword.mockRejectedValue(new Error('Current password is incorrect'));
    const user = userEvent.setup();
    renderPage();

    await fill(user, { current: 'wrong' });

    expect(await screen.findByText('Current password is incorrect')).toBeInTheDocument();

    expect(screen.getByRole('button', { name: 'Set password' })).toBeEnabled();
  });

  it('re-reads the auth status once it lands, which is what releases the app', async () => {
    changePassword.mockResolvedValue({ username: 'admin', role: 'ADMIN', password_change_required: false });
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(status).toHaveBeenCalledTimes(1));
    await fill(user);

    await waitFor(() => expect(status).toHaveBeenCalledTimes(2));
  });
});
