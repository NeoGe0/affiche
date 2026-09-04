import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { PosterBrowserModal } from './PosterBrowserModal';
import { posterTargetFromItem } from './posterTarget';
import { postersApi } from '../../api';
import { usePosterConfig } from '../../hooks';
import type { LibraryItem, PosterConfig } from '../../types';

vi.mock('../../api', () => ({
  postersApi: {
    getPosters: vi.fn(),
    getSeasonPosters: vi.fn(),
    searchPosters: vi.fn(),
    uploadCustomPoster: vi.fn(),
    getTranslatedTitle: vi.fn(),
  },
  errorMessage: (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback,
}));

vi.mock('../image', () => ({
  PosterPreview: ({ title }: { title: string }) => <div data-testid="preview">{title}</div>,
}));

const CONFIG = {
  overlay_options: { border_px: 4 },
  text_options: { font_size: 40 },
  generation_options: { jpeg_quality: 90 },
} as unknown as PosterConfig;

vi.mock('../../hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../hooks')>()),
  usePosterConfig: vi.fn(),
  useProviderStatus: () => ({
    isAnyProviderConfigured: true,
    configuredProviders: ['tmdb', 'tvdb'],
    isLoading: false,
    reload: vi.fn(),
  }),
}));

const ITEM: LibraryItem = {
  id: 1,
  library_id: 2,
  title: 'Alien',
  type: 'movie',
  year: 1979,
  tmdb_id: '348',
  processed: false,
  locked: false,
  has_poster: false,
};

const SEASON_NUMBER = 2;

const getPosters = vi.mocked(postersApi.getPosters);
const getSeasonPosters = vi.mocked(postersApi.getSeasonPosters);
const searchPosters = vi.mocked(postersApi.searchPosters);
const uploadCustomPoster = vi.mocked(postersApi.uploadCustomPoster);
const posterConfig = vi.mocked(usePosterConfig);

beforeEach(() => {
  vi.clearAllMocks();
  posterConfig.mockReturnValue({ config: CONFIG, isLoading: false, error: null });
  getPosters.mockResolvedValue([
    { url: 'https://cdn/a.jpg', provider: 'tmdb', rank: 0, rank_score: 1 },
    { url: 'https://cdn/b.jpg', provider: 'mediux', rank: 0, rank_score: 1 },
  ]);
  getSeasonPosters.mockResolvedValue([{ url: 'https://cdn/s1.jpg', provider: 'tvdb', rank: 0, rank_score: 1 }]);
});

function renderModal(props: Partial<React.ComponentProps<typeof PosterBrowserModal>> = {}) {
  const onSave = props.onSave ?? vi.fn();
  const onClose = props.onClose ?? vi.fn();
  const utils = render(
    <PosterBrowserModal
      target={posterTargetFromItem(ITEM)}
      {...props}
      onSave={onSave}
      onClose={onClose}
    />
  );
  return { ...utils, onSave, onClose };
}

const candidates = () => screen.findAllByRole('button', { name: /^Poster \d+ from / });

describe('PosterBrowserModal — filling the grid', () => {
  it('fetches immediately, textless — browsing does not wait on the poster config', async () => {

    renderModal();

    await waitFor(() => expect(getPosters).toHaveBeenCalledTimes(1));
    expect(getPosters).toHaveBeenCalledWith(
      expect.objectContaining({ tmdb_id: 348, media_type: 'movie' })
    );
    expect(getPosters.mock.calls[0][0].language).toBeUndefined();
  });

  it('refetches when the language changes', async () => {
    const user = userEvent.setup();
    renderModal();
    await waitFor(() => expect(getPosters).toHaveBeenCalledTimes(1));

    await user.selectOptions(screen.getByLabelText('Language'), 'fr');

    await waitFor(() => expect(getPosters).toHaveBeenCalledTimes(2));
    expect(getPosters.mock.calls[1][0].language).toBe('fr');
  });

  it('reorders the grid without refetching or losing the pick', async () => {

    getPosters.mockResolvedValue([
      { url: 'https://cdn/a.jpg', provider: 'tmdb', rank: 0, rank_score: 1 },
      { url: 'https://cdn/b.jpg', provider: 'tmdb', rank: 1, rank_score: 0 },
      { url: 'https://cdn/c.jpg', provider: 'mediux', rank: 0, rank_score: 1 },
    ]);
    const user = userEvent.setup();
    renderModal();
    const [first] = await candidates();
    await user.click(first);

    await user.selectOptions(screen.getByLabelText('Sort by'), 'rating');

    const sorted = await candidates();
    expect(sorted.map((button) => button.getAttribute('aria-label'))).toEqual([
      'Poster 1 from TMDB',
      'Poster 2 from MediUX',
      'Poster 3 from TMDB',
    ]);
    expect(getPosters).toHaveBeenCalledTimes(1);
    expect(sorted[0]).toHaveAttribute('aria-pressed', 'true');
  });

  it('drops the selection when the provider changes', async () => {
    const user = userEvent.setup();
    renderModal();
    const [first] = await candidates();

    await user.click(first);
    expect(first).toHaveAttribute('aria-pressed', 'true');

    await user.selectOptions(screen.getByLabelText('Provider'), 'tvdb');

    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Poster 1', pressed: true })).toBeNull()
    );
  });

  it('browses season artwork, and switches to show art on demand', async () => {
    const user = userEvent.setup();
    renderModal({ seasonNumber: SEASON_NUMBER });

    await waitFor(() => expect(getSeasonPosters).toHaveBeenCalledTimes(1));
    expect(getSeasonPosters.mock.calls[0][0].season_number).toBe(2);

    await user.click(screen.getByRole('tab', { name: 'Show art' }));

    await waitFor(() => expect(getPosters).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/still applies to Season 2/)).toBeInTheDocument();
  });

  it('replaces the grid with a title search', async () => {
    searchPosters.mockResolvedValue([{ url: 'https://cdn/search.jpg', provider: 'tmdb', rank: 0, rank_score: 1 }]);
    const user = userEvent.setup();
    renderModal();
    await candidates();

    await user.click(screen.getByRole('button', { name: 'Search' }));

    await waitFor(() => expect(searchPosters).toHaveBeenCalled());
    expect(searchPosters.mock.calls[0][0]).toMatchObject({ name: 'Alien', year: 1979 });
    await waitFor(async () => expect(await candidates()).toHaveLength(1));
  });

  it('shows the reason a fetch failed', async () => {
    getPosters.mockRejectedValue(new Error('TMDB rate limit'));

    renderModal();

    expect(await screen.findByText('TMDB rate limit')).toBeInTheDocument();
  });

  it('selects a staged custom image without touching the grid', async () => {
    uploadCustomPoster.mockResolvedValue({ token: 'abc' });
    const user = userEvent.setup();
    const { onSave } = renderModal();
    await candidates();

    await user.type(screen.getByLabelText('Use your own image'), 'https://example.com/p.jpg');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(onSave).toHaveBeenCalledWith('custom:abc', expect.anything());
  });
});

describe('PosterBrowserModal — a save in flight', () => {
  it('cannot be dismissed with Cancel', async () => {
    const { onClose } = renderModal({ isSaving: true });
    await candidates();

    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('cannot be dismissed with the close button', async () => {
    const user = userEvent.setup();
    const { onClose } = renderModal({ isSaving: true });
    await candidates();

    const close = screen.getByRole('button', { name: 'Close' });
    expect(close).toBeDisabled();
    await user.click(close);

    expect(onClose).not.toHaveBeenCalled();
  });

  it('cannot be dismissed by clicking the backdrop', async () => {
    const { container, onClose } = renderModal({ isSaving: true });
    await candidates();
    const backdrop = container.firstElementChild!;

    fireEvent.mouseDown(backdrop);
    fireEvent.mouseUp(backdrop);

    expect(onClose).not.toHaveBeenCalled();
  });

  it('closes on a backdrop click when nothing is in flight', async () => {
    const { container, onClose } = renderModal();
    await candidates();
    const backdrop = container.firstElementChild!;

    fireEvent.mouseDown(backdrop);
    fireEvent.mouseUp(backdrop);

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe('PosterBrowserModal — style drafts', () => {
  it('saves the global config values when the style was never edited', async () => {
    const user = userEvent.setup();
    const { onSave } = renderModal();
    const [first] = await candidates();

    await user.click(first);
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(onSave).toHaveBeenCalledWith('https://cdn/a.jpg', {
      overlayOptions: CONFIG.overlay_options,
      textOptions: CONFIG.text_options,
      jpegQuality: 90,
      title: 'Alien',
      upload: false,
    });
  });

  it('defaults the upload toggle to the library setting and sends it', async () => {
    const user = userEvent.setup();
    const { onSave } = renderModal({ defaultUpload: true });
    const [first] = await candidates();

    await user.click(first);
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(onSave).toHaveBeenCalledWith(
      'https://cdn/a.jpg',
      expect.objectContaining({ upload: true })
    );
  });

  it('titles a season pick with its season label', async () => {
    const user = userEvent.setup();
    const { onSave } = renderModal({ seasonNumber: SEASON_NUMBER });
    const [first] = await candidates();

    await user.click(first);
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(onSave).toHaveBeenCalledWith(
      'https://cdn/s1.jpg',
      expect.objectContaining({ title: 'Season 2' })
    );
  });
});
