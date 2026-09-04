import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';

import { ItemDetail } from './ItemDetail';
import { libraryApi } from '../../api';
import type { ItemSeason, LibraryItem, LibraryItemWithSeasons } from '../../types';

vi.mock('../../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api')>();
  return {
    ...actual,
    libraryApi: { ...actual.libraryApi, getItemWithSeasons: vi.fn() },
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

function renderDetail(props: { item?: LibraryItem; imageRefreshKey?: number } = {}) {
  const ui = (p: typeof props) => (
    <ItemDetail
      item={p.item ?? show}
      mediaServerId={1}
      imageRefreshKey={p.imageRefreshKey ?? 0}
      onBack={noop}
      onSync={noop}
      onGeneratePoster={noop}
      onReset={noop}
      onSelectPoster={noop}
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

describe('ItemDetail before/after compare', () => {
  const withSource = (overrides: Partial<LibraryItem> = {}): LibraryItem =>
    ({ ...show, has_poster: true, poster_version: 'v2',
       source_poster_version: 'v1', ...overrides });

  const toggle = () => screen.queryByRole('button', { name: /compare with original/i });

  it('offers no compare when the server artwork was never kept', async () => {

    renderDetail({ item: { ...show, source_poster_version: null } });

    expect(toggle()).not.toBeInTheDocument();
  });

  it('offers the compare once a source poster is kept', () => {
    renderDetail({ item: withSource() });

    expect(toggle()).toBeInTheDocument();
    expect(screen.queryByText('Before')).not.toBeInTheDocument();
  });

  it('swaps the poster for the wipe slider when toggled on', () => {
    renderDetail({ item: withSource() });
    expect(screen.queryByRole('slider')).not.toBeInTheDocument();

    fireEvent.click(toggle()!);

    expect(screen.getByRole('slider')).toBeInTheDocument();
  });

  it('requests the source variant for the revealed side', () => {

    renderDetail({ item: withSource() });
    fireEvent.click(toggle()!);

    const sources = screen.getAllByRole('img').map((img) => img.getAttribute('src') ?? '');

    expect(sources.some((src) => src.includes('variant=source') && src.includes('v=v1'))).toBe(true);
    expect(sources.some((src) => !src.includes('variant=') && src.includes('v=v2'))).toBe(true);
  });

  it('opens the full-size compare from the poster corner', () => {
    renderDetail({ item: withSource() });

    fireEvent.click(screen.getByRole('button', { name: /compare severance full size/i }));

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('slider')).toBeInTheDocument();
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
