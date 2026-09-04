import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ToastProvider } from '../../context/ToastContext';
import { resetPosterConfigStore } from '../../hooks/usePosterConfig';
import { resetFontsStore } from '../../hooks/useFonts';
import type { OverlayOptions, PosterConfig, StyleProfile, TextOptions } from '../../types';
import { StyleProfilesPanel } from './StyleProfilesPanel';

const CONFIG: PosterConfig = {
  overlay_options: { border_px: 10, border_color: '#000000' } as OverlayOptions,
  text_options: { all_caps: false, font_name: 'Inter.ttf' } as TextOptions,
  generation_options: { jpeg_quality: 90 },
};

const getProfiles = vi.fn();
const updateProfile = vi.fn();
const deleteProfile = vi.fn();
const createProfile = vi.fn();

vi.mock('../../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api')>()),
  settingsApi: { getPosterConfig: vi.fn(async () => CONFIG) },
  fontsApi: { getFonts: vi.fn(async () => []), getFontUrl: (name: string) => `/${name}` },
  styleProfilesApi: {
    getProfiles: () => getProfiles(),
    updateProfile: (...args: unknown[]) => updateProfile(...args),
    deleteProfile: (...args: unknown[]) => deleteProfile(...args),
    createProfile: (...args: unknown[]) => createProfile(...args),
  },
}));

const profile = (overrides: Partial<StyleProfile> = {}): StyleProfile => ({
  id: 3,
  name: 'Kids',
  overlay_options: null,
  text_options: null,
  library_count: 2,
  ...overrides,
});

beforeEach(() => {
  vi.resetAllMocks();
  resetPosterConfigStore();
  resetFontsStore();
  getProfiles.mockResolvedValue([profile()]);
});

const renderPanel = () => {
  render(
    <ToastProvider>
      <StyleProfilesPanel />
    </ToastProvider>
  );
  return userEvent.setup();
};

describe('StyleProfilesPanel', () => {
  it('says how many libraries each profile is used by', async () => {
    renderPanel();

    expect(await screen.findByText('Kids')).toBeInTheDocument();
    expect(screen.getByText('2 libraries')).toBeInTheDocument();
  });

  it('offers a first-time user both places a profile can come from', async () => {
    getProfiles.mockResolvedValue([]);
    renderPanel();

    expect(await screen.findByText(/Create one here/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'New profile' })).toBeInTheDocument();
  });

  it('lists a newly created profile without refetching', async () => {
    createProfile.mockResolvedValue(profile({ id: 9, name: 'Anime', library_count: 0 }));
    const user = renderPanel();

    await user.click(await screen.findByRole('button', { name: 'New profile' }));
    await user.type(await screen.findByLabelText('Name'), 'Anime');
    await user.click(screen.getByRole('button', { name: 'Create profile' }));

    expect(await screen.findByText('Anime')).toBeInTheDocument();
    expect(screen.getByText('Kids')).toBeInTheDocument();
    expect(getProfiles).toHaveBeenCalledTimes(1);
  });

  it('edits a profile in place, name and style together', async () => {
    updateProfile.mockResolvedValue(profile({ name: 'Kids Bright' }));
    const user = renderPanel();

    await user.click(await screen.findByRole('button', { name: 'Edit Kids' }));
    await user.clear(await screen.findByLabelText('Name'));
    await user.type(screen.getByLabelText('Name'), 'Kids Bright');
    await user.click(screen.getByRole('button', { name: 'Save profile' }));

    await waitFor(() =>
      expect(updateProfile).toHaveBeenCalledWith(3, expect.objectContaining({ name: 'Kids Bright' }))
    );
    expect(await screen.findByText('Kids Bright')).toBeInTheDocument();

    expect(screen.queryByText('Kids')).not.toBeInTheDocument();
    expect(getProfiles).toHaveBeenCalledTimes(1);
  });

  it('warns what deleting does to the libraries using it', async () => {
    const user = renderPanel();

    await user.click(await screen.findByRole('button', { name: 'Delete Kids' }));

    expect(
      screen.getByText(/2 libraries using it will fall back to the global style/)
    ).toBeInTheDocument();
  });

  it('keeps the profile listed when the delete fails', async () => {
    deleteProfile.mockRejectedValue(new Error('Still in use'));
    const user = renderPanel();

    await user.click(await screen.findByRole('button', { name: 'Delete Kids' }));
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Still in use');
    expect(screen.getByText('Kids')).toBeInTheDocument();
  });

  it('drops it from the list once the delete lands', async () => {
    deleteProfile.mockResolvedValue(undefined);
    const user = renderPanel();

    await user.click(await screen.findByRole('button', { name: 'Delete Kids' }));
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Kids')).not.toBeInTheDocument());
  });
});
