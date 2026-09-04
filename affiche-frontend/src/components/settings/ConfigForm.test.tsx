import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ConfigForm } from './ConfigForm';

type Props = Partial<React.ComponentProps<typeof ConfigForm>>;

const TEST_URL = 'https://api.tmdb.org';

function renderForm(props: Props = {}) {
  const onSave = props.onSave ?? vi.fn();
  const utils = render(
    <ConfigForm
      title="TMDB"
      serviceName="tmdb"
      serviceType="PROVIDER"
      initialUrl={TEST_URL}
      onSave={onSave}
      {...props}
    />
  );
  return { ...utils, onSave };
}

const saveButton = () => screen.getByRole('button', { name: /save/i });
const tokenField = () => screen.getByLabelText('API Token');

describe('ConfigForm', () => {
  it('starts in token-entry mode when nothing is configured yet', () => {
    renderForm();

    expect(tokenField()).toHaveValue('');
    expect(screen.queryByRole('button', { name: /change token/i })).not.toBeInTheDocument();
  });

  it('masks an already-saved token instead of rendering the secret', () => {
    renderForm({ hasStoredToken: true, storedTokenHint: 'c3et',
                 initialUrl: TEST_URL });

    expect(screen.queryByLabelText('API Token')).not.toBeInTheDocument();

    expect(screen.getByText(/c3et/)).toBeInTheDocument();
    expect(screen.getByLabelText('API URL')).toHaveValue(TEST_URL);
  });

  it('submits the edited values', async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm({ initialUrl: TEST_URL });

    await user.type(tokenField(), 'abc123');
    await user.click(saveButton());

    expect(onSave).toHaveBeenCalledWith({
      url: TEST_URL,
      token: 'abc123',
      enabled: true,
    });
  });

  it('“Change token” switches to an empty field so the stored secret is never revealed', async () => {
    const user = userEvent.setup();
    renderForm({ hasStoredToken: true });

    await user.click(screen.getByRole('button', { name: /change token/i }));

    expect(tokenField()).toHaveValue('');
  });

  it('re-saving an untouched config needs no validation', () => {
    renderForm({ hasStoredToken: true, onValidate: vi.fn() });

    expect(saveButton()).toBeEnabled();
  });

  it('omits the token when the user did not enter one, rather than sending a blank', async () => {

    const user = userEvent.setup();
    const onSave = vi.fn();
    renderForm({ hasStoredToken: true, initialEnabled: true, onSave });

    await user.click(screen.getByLabelText('Enabled'));
    await user.click(saveButton());

    expect(onSave).toHaveBeenCalledWith({ url: TEST_URL, enabled: false });
    expect(onSave.mock.calls[0][0]).not.toHaveProperty('token');
  });

  it('sends the token once the user replaces it', async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm({ hasStoredToken: true });

    await user.click(screen.getByRole('button', { name: /change token/i }));
    await user.type(tokenField(), 'replacement');
    await user.click(saveButton());

    expect(onSave).toHaveBeenCalledWith({ url: TEST_URL, token: 'replacement', enabled: true });
  });

  it('blocks the save until edited credentials are validated', async () => {
    const user = userEvent.setup();
    const onValidate = vi.fn().mockResolvedValue(true);
    renderForm({ hasStoredToken: true, onValidate });

    await user.click(screen.getByRole('button', { name: /change token/i }));
    await user.type(tokenField(), 'newtoken');
    expect(saveButton()).toBeDisabled();

    await user.click(screen.getByRole('button', { name: /validate/i }));

    expect(onValidate).toHaveBeenCalledWith(TEST_URL, 'newtoken');
    expect(saveButton()).toBeEnabled();
  });

  it('adopts config values that arrive after the first render', () => {

    const { rerender } = renderForm();

    rerender(
      <ConfigForm
        key="https://api.tmdb.org|true|true|c3et"
        title="TMDB"
        serviceName="tmdb"
        serviceType="PROVIDER"
        initialUrl={TEST_URL}
        hasStoredToken
        storedTokenHint="c3et"
        initialEnabled={false}
        onSave={vi.fn()}
      />
    );

    expect(screen.getByLabelText('API URL')).toHaveValue(TEST_URL);

    expect(screen.getByText(/c3et/)).toBeInTheDocument();
    expect(screen.getByLabelText('Enabled')).not.toBeChecked();
  });
});

describe('ConfigForm for a provider with an open API', () => {
  it('asks for no token at all', () => {
    renderForm({ hideToken: true });

    expect(screen.queryByLabelText('API Token')).not.toBeInTheDocument();
  });

  it('can still validate, since reachability is the only question left', async () => {

    const user = userEvent.setup();
    const onValidate = vi.fn().mockResolvedValue(true);
    renderForm({ hideToken: true, onValidate });

    const validate = screen.getByRole('button', { name: /validate/i });
    expect(validate).toBeEnabled();

    await user.click(validate);

    expect(onValidate).toHaveBeenCalledWith(TEST_URL, '');
  });

  it('saves without a token', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    renderForm({ hideToken: true, onSave, initialEnabled: false });

    await user.click(screen.getByLabelText('Enabled'));
    await user.click(saveButton());

    expect(onSave).toHaveBeenCalledWith({ url: TEST_URL, enabled: true });
  });
});
