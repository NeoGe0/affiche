import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import type {
  LibrarySettings,
  OverlayOptions,
  PosterConfig,
  StyleProfile,
  TextOptions,
} from '../../types';
import { ToastProvider } from '../../context/ToastContext';
import { resetPosterConfigStore } from '../../hooks/usePosterConfig';
import { resetFontsStore } from '../../hooks/useFonts';
import { LibraryStyleModal } from './LibraryStyleModal';
import { defaultLibrarySettings } from './mediaServerState';

const CONFIG: PosterConfig = {
  overlay_options: { border_px: 10, border_color: '#000000' } as OverlayOptions,
  text_options: { all_caps: false, font_name: 'Inter.ttf' } as TextOptions,
  generation_options: { jpeg_quality: 90 },
};

const getStyleStaleness = vi.fn(async () => ({ stale: 0, total: 0 }));
const getProfiles = vi.fn(async (): Promise<StyleProfile[]> => []);
const createProfile = vi.fn();

vi.mock('../../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api')>()),
  settingsApi: { getPosterConfig: vi.fn(async () => CONFIG) },
  fontsApi: { getFonts: vi.fn(async () => []), getFontUrl: (name: string) => `/${name}` },
  libraryApi: { getStyleStaleness: () => getStyleStaleness() },
  styleProfilesApi: {
    getProfiles: () => getProfiles(),
    createProfile: (...args: [never]) => createProfile(...args),
  },
}));

function renderModal(settings: LibrarySettings, onApply = vi.fn()) {
  render(
    <ToastProvider>
      <LibraryStyleModal
        libraryName="Anime"
        mediaServerId={1}
        libraryId={10}
        settings={settings}
        onApply={onApply}
        onClose={vi.fn()}
      />
    </ToastProvider>
  );
  return onApply;
}

beforeEach(() => {
  resetPosterConfigStore();
  resetFontsStore();
});

afterEach(() => {
  vi.clearAllMocks();
  getStyleStaleness.mockResolvedValue({ stale: 0, total: 0 });
  getProfiles.mockResolvedValue([]);
});

describe('LibraryStyleModal', () => {
  it('opens on Global style for a library that inherits', () => {
    renderModal(defaultLibrarySettings(10));

    expect(screen.getByRole('radio', { name: /Global style/ })).toBeChecked();
    expect(screen.getByRole('radio', { name: /Custom style/ })).not.toBeChecked();
  });

  it('opens on Custom style for a library that overrides', () => {
    renderModal({ ...defaultLibrarySettings(10), overlay_options: { border_px: 42 } });

    expect(screen.getByRole('radio', { name: /Custom style/ })).toBeChecked();
  });

  it('applies explicit nulls when handing a custom style back to the global one', async () => {
    const user = userEvent.setup();
    const onApply = renderModal({
      ...defaultLibrarySettings(10),
      overlay_options: { border_px: 42 },
      text_options: { all_caps: true },
    });

    await user.click(screen.getByRole('radio', { name: /Global style/ }));
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    expect(onApply).toHaveBeenCalledWith({
      overlay_options: null,
      text_options: null,
      style_profile_id: null,
    });
  });

  it('opens on the profile mode for a library that has one assigned', async () => {
    getProfiles.mockResolvedValue([
      { id: 3, name: 'Kids', overlay_options: null, text_options: null, library_count: 1 },
    ]);
    renderModal({ ...defaultLibrarySettings(10), style_profile_id: 3 });

    await waitFor(() => expect(getProfiles).toHaveBeenCalled());
    expect(screen.getByRole('radio', { name: /Style profile/ })).toBeChecked();
    expect(screen.getByRole('combobox')).toHaveValue('3');
  });

  it('applies a profile assignment, clearing the inline columns it would shadow', async () => {
    const user = userEvent.setup();
    getProfiles.mockResolvedValue([
      { id: 3, name: 'Kids', overlay_options: null, text_options: null, library_count: 0 },
    ]);
    const onApply = renderModal({
      ...defaultLibrarySettings(10),
      overlay_options: { border_px: 7 },
    });

    await waitFor(() => expect(getProfiles).toHaveBeenCalled());
    await user.click(screen.getByRole('radio', { name: /Style profile/ }));
    await user.selectOptions(screen.getByRole('combobox'), '3');
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    expect(onApply).toHaveBeenCalledWith({
      overlay_options: null,
      text_options: null,
      style_profile_id: 3,
    });
  });

  it('offers no profile mode until one exists', async () => {
    renderModal(defaultLibrarySettings(10));

    await waitFor(() => expect(getProfiles).toHaveBeenCalled());
    expect(screen.getByRole('radio', { name: /Style profile/ })).toBeDisabled();
  });

  it('warns how many posters predate the current style', async () => {
    getStyleStaleness.mockResolvedValue({ stale: 12, total: 340 });
    renderModal(defaultLibrarySettings(10));

    expect(await screen.findByText(/12 of 340 posters were generated with an earlier style/))
      .toBeInTheDocument();
  });

  it('stays quiet when nothing is stale', async () => {
    renderModal(defaultLibrarySettings(10));

    await waitFor(() => expect(getStyleStaleness).toHaveBeenCalled());
    expect(screen.queryByText(/earlier style/)).not.toBeInTheDocument();
  });

  it('still opens when the staleness count cannot be loaded', async () => {

    getStyleStaleness.mockRejectedValue(new Error('boom'));
    renderModal(defaultLibrarySettings(10));

    await waitFor(() => expect(getStyleStaleness).toHaveBeenCalled());
    expect(screen.getByRole('radio', { name: /Global style/ })).toBeChecked();
  });

  it('seeds a new custom style from the global defaults rather than an empty bag', async () => {
    const user = userEvent.setup();
    const onApply = renderModal(defaultLibrarySettings(10));

    await user.click(screen.getByRole('radio', { name: /Custom style/ }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    expect(onApply).toHaveBeenCalledWith({
      overlay_options: CONFIG.overlay_options,
      text_options: CONFIG.text_options,
      style_profile_id: null,
    });
  });
});
