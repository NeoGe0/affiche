import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import type { OverlayOptions, PosterConfig, StyleProfile, TextOptions } from '../../types';
import { ToastProvider } from '../../context/ToastContext';
import { resetPosterConfigStore } from '../../hooks/usePosterConfig';
import { resetFontsStore } from '../../hooks/useFonts';
import { StyleProfileModal } from './StyleProfileModal';

const CONFIG: PosterConfig = {
  overlay_options: { border_px: 10, border_color: '#000000' } as OverlayOptions,
  text_options: { all_caps: false, font_name: 'Inter.ttf' } as TextOptions,
  generation_options: { jpeg_quality: 90 },
};

const createProfile = vi.fn();
const updateProfile = vi.fn();

vi.mock('../../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api')>()),
  settingsApi: { getPosterConfig: vi.fn(async () => CONFIG) },
  fontsApi: { getFonts: vi.fn(async () => []), getFontUrl: (name: string) => `/${name}` },
  styleProfilesApi: {
    createProfile: (...args: unknown[]) => createProfile(...args),
    updateProfile: (...args: unknown[]) => updateProfile(...args),
  },
}));

const created: StyleProfile = {
  id: 7,
  name: 'Anime',
  overlay_options: { ...CONFIG.overlay_options },
  text_options: { ...CONFIG.text_options },
  library_count: 0,
};

function renderModal(profile?: StyleProfile) {
  const onSaved = vi.fn();
  const onClose = vi.fn();
  render(
    <ToastProvider>
      <StyleProfileModal profile={profile} onSaved={onSaved} onClose={onClose} />
    </ToastProvider>
  );
  return { onSaved, onClose, user: userEvent.setup() };
}

beforeEach(() => {
  resetPosterConfigStore();
  resetFontsStore();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('StyleProfileModal', () => {
  it('cannot be submitted without a name', async () => {
    renderModal();

    expect(await screen.findByRole('button', { name: 'Create profile' })).toBeDisabled();
  });

  it('creates the profile from the global style it was seeded with', async () => {
    createProfile.mockResolvedValue(created);
    const { onSaved, onClose, user } = renderModal();

    await user.type(await screen.findByLabelText('Name'), 'Anime');
    await user.click(screen.getByRole('button', { name: 'Create profile' }));

    await waitFor(() =>
      expect(createProfile).toHaveBeenCalledWith({
        name: 'Anime',
        overlay_options: CONFIG.overlay_options,
        text_options: CONFIG.text_options,
      })
    );
    expect(onSaved).toHaveBeenCalledWith(created);
    expect(onClose).toHaveBeenCalled();
  });

  it('trims the name, so a stray space cannot make a second "Anime"', async () => {
    createProfile.mockResolvedValue(created);
    const { user } = renderModal();

    await user.type(await screen.findByLabelText('Name'), '  Anime  ');
    await user.click(screen.getByRole('button', { name: 'Create profile' }));

    await waitFor(() =>
      expect(createProfile).toHaveBeenCalledWith(expect.objectContaining({ name: 'Anime' }))
    );
  });

  it('opens on the profile it was handed, and saves back to it', async () => {
    const existing: StyleProfile = { ...created, name: 'Kids', library_count: 2 };
    updateProfile.mockResolvedValue({ ...existing, name: 'Kids Bright' });
    const { onSaved, onClose, user } = renderModal(existing);

    expect(await screen.findByLabelText('Name')).toHaveValue('Kids');

    await user.clear(screen.getByLabelText('Name'));
    await user.type(screen.getByLabelText('Name'), 'Kids Bright');
    await user.click(screen.getByRole('button', { name: 'Save profile' }));

    await waitFor(() =>
      expect(updateProfile).toHaveBeenCalledWith(7, {
        name: 'Kids Bright',
        overlay_options: CONFIG.overlay_options,
        text_options: CONFIG.text_options,
      })
    );
    expect(createProfile).not.toHaveBeenCalled();
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ name: 'Kids Bright' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('says what an edit does to the libraries already following the profile', async () => {
    renderModal({ ...created, library_count: 2 });

    expect(
      await screen.findByText(/2 libraries use this profile\. Saving restyles them all/)
    ).toBeInTheDocument();
    expect(screen.getByText(/only from their next generation/)).toBeInTheDocument();
  });

  it('says nothing of the sort when no library uses it yet', async () => {
    renderModal({ ...created, library_count: 0 });

    expect(await screen.findByLabelText('Name')).toBeInTheDocument();
    expect(screen.queryByText(/Saving restyles/)).not.toBeInTheDocument();
  });

  it('stays open on the draft when the name is already taken', async () => {
    createProfile.mockRejectedValue(new Error('A style profile named "Anime" already exists'));
    const { onSaved, onClose, user } = renderModal();

    await user.type(await screen.findByLabelText('Name'), 'Anime');
    await user.click(screen.getByRole('button', { name: 'Create profile' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('already exists');
    expect(onSaved).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Name')).toHaveValue('Anime');
  });
});
