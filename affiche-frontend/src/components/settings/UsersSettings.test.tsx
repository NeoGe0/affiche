import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { UsersSettings } from './UsersSettings';
import { AuthProvider } from '../../context/AuthContext';
import { ToastProvider } from '../../context/ToastContext';
import { authApi } from '../../api';
import type { AuthStatus, UserAccount, UserRole } from '../../types';

vi.mock('../../api', () => ({
  authApi: {
    status: vi.fn(),
    login: vi.fn(),
    setup: vi.fn(),
    logout: vi.fn(),
    me: vi.fn(),
    changePassword: vi.fn(),
    listUsers: vi.fn(),
    createUser: vi.fn(),
    setUserRole: vi.fn(),
    deleteUser: vi.fn(),
  },
  errorMessage: (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback,
}));

const status = vi.mocked(authApi.status);
const changePassword = vi.mocked(authApi.changePassword);
const listUsers = vi.mocked(authApi.listUsers);
const createUser = vi.mocked(authApi.createUser);
const setUserRole = vi.mocked(authApi.setUserRole);
const deleteUser = vi.mocked(authApi.deleteUser);

const CURRENT = 'the-one-i-know';
const CHOSEN = 'the-one-i-want';

const account = (id: number, username: string, role: UserRole): UserAccount =>
  ({ id, username, role, password_change_required: false });

const BOSS = account(1, 'boss', 'ADMIN');
const HELPER = account(2, 'helper', 'OPERATOR');

const signedInAs = (role: UserRole): AuthStatus => ({
  setup_required: false,
  authenticated: true,
  username: 'boss',
  role,
  password_change_required: false,
});

beforeEach(() => {
  vi.resetAllMocks();
  status.mockResolvedValue(signedInAs('ADMIN'));
  listUsers.mockResolvedValue([BOSS, HELPER]);
});

const renderTab = () =>
  render(
    <ToastProvider>
      <AuthProvider>
        <UsersSettings />
      </AuthProvider>
    </ToastProvider>
  );

const fillPasswordForm = async (
  user: ReturnType<typeof userEvent.setup>,
  { current = CURRENT, next = CHOSEN, confirm = CHOSEN } = {}
) => {
  await user.type(screen.getByLabelText('Current password'), current);
  await user.type(screen.getByLabelText('New password'), next);
  await user.type(screen.getByLabelText('Confirm new password'), confirm);
  await user.click(screen.getByRole('button', { name: 'Change password' }));
};

describe('UsersSettings own account', () => {
  it('names the signed-in account and its role', async () => {
    renderTab();

    expect(await screen.findByText('This is you')).toBeInTheDocument();
    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0);
  });

  it('sends both passwords and empties the form once it lands', async () => {
    changePassword.mockResolvedValue({ username: 'boss', role: 'ADMIN', password_change_required: false });
    const user = userEvent.setup();
    renderTab();

    await fillPasswordForm(user);

    await waitFor(() => expect(changePassword).toHaveBeenCalledWith(CURRENT, CHOSEN));
    await waitFor(() => expect(screen.getByLabelText('Current password')).toHaveValue(''));
  });

  it('refuses a mistyped confirmation without asking the backend', async () => {
    const user = userEvent.setup();
    renderTab();

    await fillPasswordForm(user, { confirm: 'not-the-same' });

    expect(await screen.findByRole('alert')).toHaveTextContent(/different/);
    expect(changePassword).not.toHaveBeenCalled();
  });

  it('keeps what was typed when the backend rejects it, and says why', async () => {
    changePassword.mockRejectedValue(new Error('Current password is incorrect'));
    const user = userEvent.setup();
    renderTab();

    await fillPasswordForm(user, { current: 'wrong' });

    expect(await screen.findByRole('alert')).toHaveTextContent('Current password is incorrect');
    expect(screen.getByLabelText('New password')).toHaveValue(CHOSEN);
  });
});

describe('UsersSettings account management', () => {
  it('lists every account with its role', async () => {
    renderTab();

    expect(await screen.findByText('helper')).toBeInTheDocument();
    expect(screen.getByText('Operator')).toBeInTheDocument();
  });

  it('creates an operator by default', async () => {
    createUser.mockResolvedValue(account(3, 'newcomer', 'OPERATOR'));
    const user = userEvent.setup();
    renderTab();

    await user.click(await screen.findByRole('button', { name: /Add user/ }));
    await user.type(screen.getByLabelText('Username'), 'newcomer');
    await user.type(screen.getByLabelText('Password'), 'a-good-password');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() =>
      expect(createUser).toHaveBeenCalledWith('newcomer', 'a-good-password', 'OPERATOR'));
  });

  it('can create an admin when that is asked for explicitly', async () => {
    createUser.mockResolvedValue(account(3, 'second-boss', 'ADMIN'));
    const user = userEvent.setup();
    renderTab();

    await user.click(await screen.findByRole('button', { name: /Add user/ }));
    await user.type(screen.getByLabelText('Username'), 'second-boss');
    await user.type(screen.getByLabelText('Password'), 'a-good-password');

    await user.click(screen.getByRole('radio', { name: /^Admin/ }));
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() =>
      expect(createUser).toHaveBeenCalledWith('second-boss', 'a-good-password', 'ADMIN'));
  });

  it('shows the new account without a refetch', async () => {
    createUser.mockResolvedValue(account(3, 'newcomer', 'OPERATOR'));
    const user = userEvent.setup();
    renderTab();

    await user.click(await screen.findByRole('button', { name: /Add user/ }));
    await user.type(screen.getByLabelText('Username'), 'newcomer');
    await user.type(screen.getByLabelText('Password'), 'a-good-password');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByText('newcomer')).toBeInTheDocument();
    expect(listUsers).toHaveBeenCalledTimes(1);
  });

  it('reports a rejected creation and keeps the form open', async () => {
    createUser.mockRejectedValue(new Error("An account named 'helper' already exists"));
    const user = userEvent.setup();
    renderTab();

    await user.click(await screen.findByRole('button', { name: /Add user/ }));
    await user.type(screen.getByLabelText('Username'), 'helper');
    await user.type(screen.getByLabelText('Password'), 'a-good-password');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('already exists');
    expect(screen.getByLabelText('Username')).toHaveValue('helper');
  });

  it('confirms before removing an account, and only then calls the backend', async () => {
    deleteUser.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderTab();

    await user.click(await screen.findByRole('button', { name: 'Remove helper' }));
    expect(deleteUser).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Remove' }));

    await waitFor(() => expect(deleteUser).toHaveBeenCalledWith(2));
    await waitFor(() => expect(screen.queryByText('helper')).not.toBeInTheDocument());
  });

  it('offers no way to remove the account you are signed in as', async () => {
    renderTab();

    await screen.findByText('helper');
    expect(screen.queryByRole('button', { name: 'Remove boss' })).not.toBeInTheDocument();
  });
});

describe('UsersSettings role changes', () => {

  const openEditor = async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByRole('button', { name: 'Edit helper' }));
    return user;
  };

  const roleOption = (role: 'Admin' | 'Operator') => screen.getByRole('radio', { name: new RegExp(`^${role}`) });

  it('opens on the role the account already has', async () => {
    await openEditor();

    expect(roleOption('Operator')).toBeChecked();
    expect(roleOption('Admin')).not.toBeChecked();
  });

  it('asks nothing of the backend until the change is confirmed', async () => {
    const user = await openEditor();

    await user.click(roleOption('Admin'));

    expect(setUserRole).not.toHaveBeenCalled();
  });

  it('sends the new role on save and shows what came back', async () => {
    setUserRole.mockResolvedValue(account(2, 'helper', 'ADMIN'));
    const user = await openEditor();

    await user.click(roleOption('Admin'));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() => expect(setUserRole).toHaveBeenCalledWith(2, 'ADMIN'));

    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Save changes' })).not.toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Edit helper' }));
    expect(roleOption('Admin')).toBeChecked();
  });

  it('cannot be saved until something is actually different', async () => {
    await openEditor();

    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  });

  it('stays open with the choice intact when the backend refuses', async () => {
    setUserRole.mockRejectedValue(new Error('You cannot change your own role'));
    const user = await openEditor();

    await user.click(roleOption('Admin'));
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('You cannot change your own role');
    expect(roleOption('Admin')).toBeChecked();
  });

  it('discards the choice when the dialog is cancelled', async () => {
    const user = await openEditor();

    await user.click(roleOption('Admin'));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(setUserRole).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Edit helper' }));
    expect(roleOption('Operator')).toBeChecked();
  });

  it('offers neither button for the account you are signed in as', async () => {
    renderTab();

    await screen.findByText('This is you');

    expect(screen.queryByRole('button', { name: 'Edit boss' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Remove boss' })).not.toBeInTheDocument();
  });
});

describe('UsersSettings account creation', () => {
  const openCreator = async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByRole('button', { name: /Add user/ }));
    return user;
  };

  it('opens on the limited role, so an admin is asked for rather than assumed', async () => {
    await openCreator();

    expect(screen.getByRole('radio', { name: /^Operator/ })).toBeChecked();
  });

  it('cannot be submitted until both fields are filled', async () => {
    const user = await openCreator();
    const create = () => screen.getByRole('button', { name: 'Create account' });

    expect(create()).toBeDisabled();

    await user.type(screen.getByLabelText('Username'), 'newcomer');
    expect(create()).toBeDisabled();

    await user.type(screen.getByLabelText('Password'), 'a-good-password');
    expect(create()).toBeEnabled();
  });

  it('keeps the dialog and its contents when the backend refuses', async () => {
    createUser.mockRejectedValue(new Error('An account named "newcomer" already exists'));
    const user = await openCreator();

    await user.type(screen.getByLabelText('Username'), 'newcomer');
    await user.type(screen.getByLabelText('Password'), 'a-good-password');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('already exists');

    expect(screen.getByLabelText('Username')).toHaveValue('newcomer');
  });

  it('starts empty again after one was created', async () => {
    createUser.mockResolvedValue(account(3, 'newcomer', 'OPERATOR'));
    const user = await openCreator();

    await user.type(screen.getByLabelText('Username'), 'newcomer');
    await user.type(screen.getByLabelText('Password'), 'a-good-password');
    await user.click(screen.getByRole('button', { name: 'Create account' }));
    await waitFor(() => expect(createUser).toHaveBeenCalled());

    await user.click(screen.getByRole('button', { name: /Add user/ }));
    expect(screen.getByLabelText('Username')).toHaveValue('');
  });
});

describe('UsersSettings as an operator', () => {
  beforeEach(() => {
    status.mockResolvedValue(signedInAs('OPERATOR'));
  });

  it('still offers the password change', async () => {
    renderTab();

    expect(await screen.findByLabelText('Current password')).toBeInTheDocument();
  });

  it('does not ask for the account list it would be refused', async () => {
    renderTab();

    await screen.findByLabelText('Current password');
    expect(listUsers).not.toHaveBeenCalled();
  });

  it('offers no account management', async () => {
    renderTab();

    await screen.findByLabelText('Current password');
    expect(screen.queryByRole('button', { name: /Add user/ })).not.toBeInTheDocument();
    expect(screen.queryByText('All accounts')).not.toBeInTheDocument();
  });
});
