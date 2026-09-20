import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';

import { ItemDetail } from './ItemDetail';
import { resetItemArtworkCache } from '../../hooks/useItemArtwork';
import { libraryApi, postersApi } from '../../api';
import type { ItemSeason, LibraryItem, LibraryItemWithSeasons } from '../../types';

vi.mock('../../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api')>();
  return {
    ...actual,
    libraryApi: { ...actual.libraryApi, getItemWithSeasons: vi.fn() },
    postersApi: { ...actual.postersApi, getPosters: vi.fn() },
  };
});

const toast = { error: vi.fn(), success: vi.fn(), info: vi.fn(), show: vi.fn() };
vi.mock('../../context/ToastContext', () => ({
  useToast: () => toast,
}));

const getItemWithSeasons = vi.mocked(libraryApi.getItemWithSeasons);

const show: LibraryItem = {
  id: 7,
  library_id: 3,
  title: 'Severance',
  type: 'show',
  processed: true,
  locked: false,
};

const season = (n: number): ItemSeason =>
  ({ id: n, show_id: 7, library_id: 3, season_number: n, title: `Season ${n}`, processed: true });

const withSeasons = (...numbers: number[]) =>
  ({ ...show, seasons: numbers.map(season) }) as unknown as LibraryItemWithSeasons;

const noop = () => {};

function renderDetail(
  props: {
    item?: LibraryItem; imageRefreshKey?: number; onSelectPoster?: (url?: string) => void;
    uploadsAutomatically?: boolean;
  } = {}
) {
  const ui = (p: typeof props) => (
    <ItemDetail
      item={p.item ?? show}
      mediaServerId={1}
      mediaServerName="Plex"
      imageRefreshKey={p.imageRefreshKey ?? 0}
      onBack={noop}
      onSync={noop}
      onGeneratePoster={noop}
      uploadsAutomatically={p.uploadsAutomatically}
      onReset={noop}
      onSelectPoster={p.onSelectPoster ?? noop}
      onUpload={noop}
      onToggleLock={noop}
    />
  );
  const utils = render(ui(props));
  return { ...utils, rerenderWith: (p: typeof props) => utils.rerender(ui(p)) };
}

const spinner = () => screen.queryByText(/loading seasons/i);

const findSeason = (n: number) => screen.findAllByText(`Season ${n}`);
const seasonShown = (n: number) => screen.queryAllByText(`Season ${n}`).length > 0;

beforeEach(() => {
  resetItemArtworkCache();
  vi.mocked(postersApi.getPosters).mockResolvedValue([]);
  getItemWithSeasons.mockReset();
  toast.error.mockReset();
});

describe('ItemDetail seasons', () => {
  it('shows the spinner during the first load, then the seasons', async () => {
    getItemWithSeasons.mockResolvedValue(withSeasons(1, 2));

    renderDetail();
    expect(spinner()).toBeInTheDocument();

    expect(await findSeason(1)).not.toHaveLength(0);
    expect(spinner()).not.toBeInTheDocument();
  });

  it('refetches silently when imageRefreshKey bumps', async () => {

    getItemWithSeasons.mockResolvedValue(withSeasons(1, 2));
    const { rerenderWith } = renderDetail();
    await findSeason(1);

    rerenderWith({ imageRefreshKey: 1 });

    expect(spinner()).not.toBeInTheDocument();
    expect(seasonShown(1)).toBe(true);
    await waitFor(() => expect(getItemWithSeasons).toHaveBeenCalledTimes(2));
  });

  it('shows the spinner again when switching to a different show', async () => {
    getItemWithSeasons.mockResolvedValue(withSeasons(1));
    const { rerenderWith } = renderDetail();
    await findSeason(1);

    getItemWithSeasons.mockReturnValue(new Promise(() => {}));
    rerenderWith({ item: { ...show, id: 99, title: 'Other' } });

    expect(spinner()).toBeInTheDocument();
  });

  it('stops the spinner when the seasons request fails', async () => {

    getItemWithSeasons.mockRejectedValue(new Error('boom'));

    renderDetail();

    await waitFor(() => expect(spinner()).not.toBeInTheDocument());
  });

  it('says the seasons could not be loaded rather than reporting none', async () => {

    getItemWithSeasons.mockRejectedValue(new Error('502'));

    renderDetail();

    expect(await screen.findByText('Could not load seasons.')).toBeInTheDocument();
    expect(screen.queryByText('No seasons found')).not.toBeInTheDocument();
    expect(toast.error).toHaveBeenCalledWith('502', { title: 'Seasons' });
  });

  it('keeps the loaded seasons, and stays quiet, when a background refetch fails', async () => {

    getItemWithSeasons.mockResolvedValue(withSeasons(1, 2));
    const { rerenderWith } = renderDetail();
    await findSeason(1);

    getItemWithSeasons.mockRejectedValue(new Error('502'));
    rerenderWith({ imageRefreshKey: 1 });

    await waitFor(() => expect(getItemWithSeasons).toHaveBeenCalledTimes(2));
    expect(seasonShown(1)).toBe(true);
    expect(screen.queryByText('Could not load seasons.')).not.toBeInTheDocument();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it('does not fetch seasons for a movie', () => {
    renderDetail({ item: { ...show, type: 'movie' } });

    expect(getItemWithSeasons).not.toHaveBeenCalled();
    expect(spinner()).not.toBeInTheDocument();
  });
});

describe('ItemDetail before/after fade', () => {
  const withSource = (overrides: Partial<LibraryItem> = {}): LibraryItem =>
    ({ ...show, has_poster: true, poster_version: 'v2',
       source_poster_version: 'v1', ...overrides });

  const fader = () => screen.queryByRole('slider', { name: /fade between the original/i });

  it('offers no fade when the server artwork was never kept', () => {

    renderDetail({ item: { ...show, source_poster_version: null } });

    expect(fader()).not.toBeInTheDocument();
  });

  it('fades between the source and the generated poster once a source is kept', () => {

    renderDetail({ item: withSource() });

    expect(fader()).toBeInTheDocument();
    const sources = screen.getAllByRole('img').map((img) => img.getAttribute('src') ?? '');
    expect(sources.some((src) => src.includes('variant=source') && src.includes('v=v1'))).toBe(true);
    expect(sources.some((src) => !src.includes('variant=') && src.includes('v=v2'))).toBe(true);
  });

  it('offers a full-size compare per season, never at thumbnail size', async () => {

    getItemWithSeasons.mockResolvedValue({
      ...show,
      seasons: [{ ...season(1), has_poster: true, poster_version: 's2', source_poster_version: 's1' }],
    } as unknown as LibraryItemWithSeasons);
    renderDetail({ item: withSource() });

    fireEvent.click(await screen.findByRole('button', { name: /compare season 1 with the original/i }));

    const dialog = screen.getByRole('dialog');
    const sources = within(dialog).getAllByRole('img').map((img) => img.getAttribute('src') ?? '');
    expect(sources.some((src) => src.includes('variant=source') && src.includes('v=s1'))).toBe(true);
    expect(sources.some((src) => !src.includes('variant=') && src.includes('v=s2'))).toBe(true);
    expect(sources.every((src) => !src.includes('size=thumb'))).toBe(true);
  });

  it('offers no season compare when that season has no kept artwork', async () => {
    getItemWithSeasons.mockResolvedValue(withSeasons(1));
    renderDetail({ item: withSource() });
    await findSeason(1);

    expect(screen.queryByRole('button', { name: /compare season 1 with the original/i }))
      .not.toBeInTheDocument();
  });
});

describe('ItemDetail failure banner', () => {
  const failed = (overrides: Partial<LibraryItem> = {}): LibraryItem =>
    ({ ...show, type: 'movie', processed: false, error_message: 'No poster found', ...overrides });

  it('keeps the walkthrough collapsed until asked for it', () => {
    renderDetail({ item: failed({ error_cause: 'identifier_mismatch' }) });

    expect(screen.getByText(/no poster found/i)).toBeInTheDocument();
    expect(screen.getByText(/no IMDb or TVDB id/i)).toBeInTheDocument();
    const toggle = screen.getByRole('button', { name: /no IMDb or TVDB id/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('list')).not.toBeInTheDocument();

    fireEvent.click(toggle);

    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText(/fix match in plex/i)).toBeInTheDocument();
  });

  it('shows the error alone when the failure has no diagnosed cause', () => {
    renderDetail({ item: failed() });

    expect(screen.getByText(/no poster found/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /IMDb or TVDB/i })).not.toBeInTheDocument();
  });
});

describe('ItemDetail actions', () => {
  const movie = (overrides: Partial<LibraryItem> = {}): LibraryItem =>
    ({ ...show, type: 'movie', processed: false, ...overrides });

  it('fills in upload for a generated poster and says what it replaces', () => {
    renderDetail({ item: movie({ processed: true }) });

    expect(screen.getByRole('button', { name: /upload to plex/i })).toBeInTheDocument();
    expect(screen.getByText(/replaces the poster plex shows for this movie/i)).toBeInTheDocument();
    expect(screen.getByText(/reset puts it back/i)).toBeInTheDocument();
  });

  it('says where a generated poster goes, now that generating one item does not ask first', () => {
    renderDetail({ item: movie(), uploadsAutomatically: true });
    expect(screen.getByText(/goes straight to Plex/)).toBeInTheDocument();
  });

  it('says a generated poster stays in Affiche for a library that does not upload', () => {
    renderDetail({ item: movie(), uploadsAutomatically: false });
    expect(screen.getByText(/stays in Affiche until you upload it/)).toBeInTheDocument();
  });

  it('offers no upload once the poster is on the server', () => {
    renderDetail({ item: movie({ processed: true, poster_uploaded_at: '2026-09-01T10:00:00Z' }) });

    expect(screen.queryByRole('button', { name: /upload to/i })).not.toBeInTheDocument();
    expect(screen.getByText('On server')).toBeInTheDocument();
  });

  it('opens the picker on the provider poster picked from the strip', async () => {
    vi.mocked(postersApi.getPosters).mockResolvedValue([
      { url: 'https://img.example/alien.jpg', provider: 'tmdb', rank: 0, rank_score: 1 },
    ]);
    const onSelectPoster = vi.fn();
    renderDetail({ item: movie({ tmdb_id: '348' }), onSelectPoster });

    fireEvent.click(await screen.findByRole('button', { name: /use poster 1 from/i }));
    expect(onSelectPoster).toHaveBeenCalledWith('https://img.example/alien.jpg');

    fireEvent.click(screen.getByRole('button', { name: /search, paste a url or pick a file/i }));
    expect(onSelectPoster).toHaveBeenLastCalledWith();
  });
});

describe('ItemDetail stepping through the listing', () => {
  function renderStepper() {
    const onPrevious = vi.fn();
    const onNext = vi.fn();
    render(
      <ItemDetail
        item={{ ...show, type: 'movie' }}
        mediaServerId={1}
        onBack={noop}
        previousItem={{ title: 'Alien' }}
        nextItem={{ title: 'Heat' }}
        onPrevious={onPrevious}
        onNext={onNext}
        onSync={noop}
        onGeneratePoster={noop}
        onReset={noop}
        onSelectPoster={noop}
        onUpload={noop}
        onToggleLock={noop}
      />
    );
    return { onPrevious, onNext };
  }

  it('steps with the buttons and with the arrow keys', () => {
    const { onPrevious, onNext } = renderStepper();

    fireEvent.click(screen.getByRole('button', { name: /Heat/ }));
    fireEvent.keyDown(window, { key: 'ArrowLeft' });

    expect(onNext).toHaveBeenCalledTimes(1);
    expect(onPrevious).toHaveBeenCalledTimes(1);
  });

  it('leaves the arrow keys to a slider or field that has focus', () => {
    const { onPrevious } = renderStepper();
    const field = document.createElement('input');
    document.body.appendChild(field);

    fireEvent.keyDown(field, { key: 'ArrowLeft' });

    expect(onPrevious).not.toHaveBeenCalled();
    field.remove();
  });
});
