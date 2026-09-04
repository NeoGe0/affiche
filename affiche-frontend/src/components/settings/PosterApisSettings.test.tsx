import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { PosterApisSettings } from './PosterApisSettings';
import { ToastProvider } from '../../context/ToastContext';
import { configApi, serviceApi } from '../../api';
import type { ServiceConfiguration } from '../../types';

vi.mock('../../api', () => ({
  configApi: { createConfig: vi.fn(), getConfig: vi.fn() },
  serviceApi: { testProvider: vi.fn() },

  errorMessage: (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback,
}));

const config = (name: string, overrides: Partial<ServiceConfiguration> = {}) =>
  ({
    name,
    type: 'PROVIDER',
    url: `https://api.${name}.com`,

    configured: true,
    token_hint: 'ken1',
    enabled: true,
    ...overrides,
  }) as ServiceConfiguration;

const createConfig = vi.mocked(configApi.createConfig);
const testProvider = vi.mocked(serviceApi.testProvider);

beforeEach(() => {
  vi.resetAllMocks();
  createConfig.mockResolvedValue(config('tmdb'));
  testProvider.mockResolvedValue({} as never);
});

const NO_TOKEN = { configured: false, token_hint: null } as const;
const ALL_ADDED = {
  tmdb: config('tmdb'),
  tvdb: config('tvdb', NO_TOKEN),
  fanart: config('fanart', NO_TOKEN),
  mediux: config('mediux', NO_TOKEN),

  tvmaze: config('tvmaze', { ...NO_TOKEN, enabled: false }),
  shoko: config('shoko', NO_TOKEN),
};

const renderScreen = (overrides: Partial<Parameters<typeof PosterApisSettings>[0]> = {}) =>
  render(
    <ToastProvider>
      <PosterApisSettings configs={ALL_ADDED} onConfigSaved={vi.fn()} {...overrides} />
    </ToastProvider>
  );

const openCard = async (label: string) => {
  const user = userEvent.setup();
  renderScreen();
  await user.click(screen.getByRole('button', { name: new RegExp(`^${label}`) }));
  return user;
};

describe('PosterApisSettings save failures', () => {
  it('says why when the save is rejected', async () => {
    createConfig.mockRejectedValue(new Error('UNIQUE constraint failed'));

    const user = await openCard('TMDB');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('UNIQUE constraint failed');
  });

  it('does not report a save that never landed as done', async () => {
    const onConfigSaved = vi.fn();
    createConfig.mockRejectedValue(new Error('boom'));

    const user = userEvent.setup();
    renderScreen({ onConfigSaved });
    await user.click(screen.getByRole('button', { name: /^TMDB/ }));
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await screen.findByRole('alert');
    expect(onConfigSaved).not.toHaveBeenCalled();
  });

  it('confirms a save that did land', async () => {
    const user = await openCard('TMDB');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/saved/i);
  });
});

describe('PosterApisSettings open-API provider', () => {
  it('reads as configured without a token', async () => {
    renderScreen();

    expect(screen.getByRole('button', { name: /^TVmaze/ })).not.toHaveTextContent('Not configured');
    expect(screen.getByRole('button', { name: /^TVDB/ })).toHaveTextContent('Not configured');
  });

  it('opens with the Enabled checkbox matching its stored state', async () => {

    await openCard('TVmaze');

    expect(screen.getByLabelText('Enabled')).not.toBeChecked();
  });

  it('asks for no API token', async () => {
    await openCard('TVmaze');

    expect(screen.queryByLabelText('API Token')).not.toBeInTheDocument();
  });

  it('saves the enabled toggle without sending a token', async () => {
    const user = await openCard('TVmaze');

    await user.click(screen.getByLabelText('Enabled'));
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() =>
      expect(createConfig).toHaveBeenCalledWith({
        name: 'tvmaze',
        type: 'PROVIDER',
        url: 'https://api.tvmaze.com',
        token: undefined,
        enabled: true,
      })
    );
  });
});

describe('PosterApisSettings stored tokens', () => {
  it('never puts a provider key in the DOM', async () => {

    await openCard('TMDB');

    expect(screen.queryByDisplayValue(/tmdb-token/)).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/tmdb-token/);
  });

  it('toggling Enabled on a configured provider does not clear its token', async () => {

    const user = await openCard('TMDB');

    await user.click(screen.getByLabelText('Enabled'));
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => expect(createConfig).toHaveBeenCalled());
    expect(createConfig.mock.calls[0][0].token).toBeUndefined();
  });

  it('shows the stored key by its hint rather than its value', async () => {
    await openCard('TMDB');

    expect(screen.getByText(/ken1/)).toBeInTheDocument();
  });
});

describe('PosterApisSettings URL field', () => {
  it('lets a self-hosted provider be given its address', async () => {

    const user = await openCard('Shoko');

    const url = screen.getByLabelText('API URL');
    expect(url).toBeEnabled();

    await user.clear(url);
    await user.type(url, 'http://192.168.1.50:8111');
    expect(url).toHaveValue('http://192.168.1.50:8111');
  });

  it('shows a public provider its address without letting it be edited', async () => {

    await openCard('TMDB');

    expect(screen.getByLabelText('API URL')).toBeDisabled();
  });

  it('offers no URL field for a provider whose client cannot use one', async () => {

    await openCard('TVDB');

    expect(screen.queryByLabelText('API URL')).not.toBeInTheDocument();
  });

  it('sends the typed URL when testing a self-hosted provider', async () => {

    const user = await openCard('Shoko');

    await user.clear(screen.getByLabelText('API URL'));
    await user.type(screen.getByLabelText('API URL'), 'http://nas:8111');
    await user.type(screen.getByLabelText('API Token'), 'a-key');
    await user.click(screen.getByRole('button', { name: /validate/i }));

    await waitFor(() => expect(testProvider).toHaveBeenCalledWith(
      'shoko', 'a-key', 'http://nas:8111'));
  });
});
