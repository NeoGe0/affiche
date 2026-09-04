import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { GeneralSettings } from './GeneralSettings';
import { settingsApi } from '../../api';
import type { AppSettings } from '../../types';

vi.mock('../../api', () => ({
  settingsApi: {
    getSettings: vi.fn(),
    getSettingsInfo: vi.fn(),
    updateSettings: vi.fn(),
  },

  errorMessage: (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback,
}));

const toast = { error: vi.fn(), success: vi.fn(), info: vi.fn(), show: vi.fn() };
vi.mock('../../context/ToastContext', () => ({
  useToast: () => toast,
}));

const settings = (overrides: Partial<AppSettings> = {}) =>
  ({
    trash_retention_days: 30,
    log_level: 'INFO',
    new_library_provider_order: ['tmdb', 'tvdb', 'fanart'],
    new_library_enabled: true,
    new_library_upload_enabled: true,
    ...overrides,
  }) as AppSettings;

const getSettings = vi.mocked(settingsApi.getSettings);
const getSettingsInfo = vi.mocked(settingsApi.getSettingsInfo);
const updateSettings = vi.mocked(settingsApi.updateSettings);

beforeEach(() => {
  getSettings.mockResolvedValue(settings());
  getSettingsInfo.mockResolvedValue({} as never);
  updateSettings.mockReset();
  toast.error.mockReset();
});

const retentionInput = async () => {
  const input = (await screen.findAllByRole('spinbutton'))[0];
  await waitFor(() => expect(input).toHaveValue(30));
  return input;
};

describe('GeneralSettings retention draft', () => {
  it('seeds the input from the loaded settings', async () => {
    render(<GeneralSettings />);

    expect(await retentionInput()).toHaveValue(30);
  });

  it('persists a valid change on blur', async () => {
    const user = userEvent.setup();
    updateSettings.mockResolvedValue(settings({ trash_retention_days: 7 }));
    render(<GeneralSettings />);
    const input = await retentionInput();

    await user.clear(input);
    await user.type(input, '7');
    await user.tab();

    await waitFor(() =>
      expect(updateSettings).toHaveBeenCalledWith({ trash_retention_days: 7 })
    );
  });

  it('reverts an unparseable value on blur without saving', async () => {
    const user = userEvent.setup();
    render(<GeneralSettings />);
    const input = await retentionInput();

    await user.clear(input);
    await user.tab();

    expect(updateSettings).not.toHaveBeenCalled();
    await waitFor(() => expect(input).toHaveValue(30));
  });

  it('does not save when the value is unchanged', async () => {
    const user = userEvent.setup();
    render(<GeneralSettings />);
    const input = await retentionInput();

    await user.click(input);
    await user.tab();

    expect(updateSettings).not.toHaveBeenCalled();
  });

  it('shows the persisted value after a successful save', async () => {
    const user = userEvent.setup();
    updateSettings.mockResolvedValue(settings({ trash_retention_days: 14 }));
    render(<GeneralSettings />);
    const input = await retentionInput();

    await user.clear(input);
    await user.type(input, '14');
    await user.tab();

    await waitFor(() => expect(input).toHaveValue(14));
  });
});

describe('GeneralSettings failures', () => {
  it('reports a save the backend refused', async () => {
    const user = userEvent.setup();
    updateSettings.mockRejectedValue(new Error('Database is locked'));
    render(<GeneralSettings />);
    const input = await retentionInput();

    await user.clear(input);
    await user.type(input, '7');
    await user.tab();

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Database is locked', { title: 'General settings' })
    );
  });

  it('says the settings could not be loaded instead of loading forever', async () => {
    getSettings.mockRejectedValue(new Error('502'));

    render(<GeneralSettings />);

    expect(await screen.findByText('Could not load settings.')).toBeInTheDocument();
    expect(toast.error).toHaveBeenCalledWith('502', { title: 'General settings' });
  });
});
