import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { RenameItemModal } from './RenameItemModal';
import { libraryApi } from '../../api';
import type { ItemTitleSuggestions } from '../../types';

vi.mock('../../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api')>();
  return {
    ...actual,
    libraryApi: { ...actual.libraryApi, suggestItemTitles: vi.fn() },
  };
});

const toast = { error: vi.fn(), success: vi.fn(), info: vi.fn(), show: vi.fn() };
vi.mock('../../context/ToastContext', () => ({ useToast: () => toast }));

const suggestItemTitles = vi.mocked(libraryApi.suggestItemTitles);

const suggestions: ItemTitleSuggestions = {
  current: 'My.movie.2012.1080p',
  matched: { title: 'My Movie', provider: 'tmdb' },
};

const onConfirm = vi.fn();

const renderModal = () =>
  render(
    <RenameItemModal
      mediaServerId={1}
      libraryId={3}
      itemId={7}
      currentTitle="My.movie.2012.1080p"
      mediaServerName="Plex"
      onConfirm={onConfirm}
      onClose={vi.fn()}
    />
  );

const field = () => screen.getByLabelText('Title') as HTMLInputElement;

beforeEach(() => {
  vi.clearAllMocks();
  suggestItemTitles.mockResolvedValue(suggestions);
});

describe('RenameItemModal', () => {
  it('offers the catalogue name for the id and pre-fills it', async () => {
    renderModal();

    await waitFor(() => expect(field().value).toBe('My Movie'));
    expect(screen.getByText('TMDB · matched by id')).toBeInTheDocument();
  });

  it('says why there is nothing to offer for an item with no id', async () => {
    suggestItemTitles.mockResolvedValue({
      current: 'My.movie.2012.1080p', matched: null, reason: 'no_id',
    });
    renderModal();

    await waitFor(() => expect(screen.getByText(/never matched it/)).toBeInTheDocument());

    expect(screen.queryByText(/matched by id/)).not.toBeInTheDocument();
    expect(field().value).toBe('My.movie.2012.1080p');
  });

  it('does not blame the media server for an item whose title already agrees', async () => {
    suggestItemTitles.mockResolvedValue({
      current: 'A Complete Unknown', matched: null, reason: 'already_correct',
    });
    renderModal();

    await waitFor(() => expect(screen.getByText(/already matches/)).toBeInTheDocument());
    expect(screen.queryByText(/never matched it/)).not.toBeInTheDocument();
  });

  it('leaves a title the user typed before the suggestions landed alone', async () => {
    let resolve: (value: ItemTitleSuggestions) => void = () => {};
    suggestItemTitles.mockReturnValue(new Promise((r) => { resolve = r; }));
    renderModal();

    fireEvent.change(field(), { target: { value: 'What I meant' } });
    resolve(suggestions);

    await waitFor(() => expect(screen.getByText('TMDB · matched by id')).toBeInTheDocument());
    expect(field().value).toBe('What I meant');
  });

  it('stays usable when the lookup fails', async () => {
    suggestItemTitles.mockRejectedValue(new Error('tmdb is down'));
    renderModal();

    await waitFor(() => expect(screen.getByText(/Could not reach the catalogue/)).toBeInTheDocument());
    expect(toast.error).toHaveBeenCalled();

    fireEvent.change(field(), { target: { value: 'My Movie' } });
    fireEvent.click(screen.getByRole('button', { name: 'Rename' }));
    expect(onConfirm).toHaveBeenCalledWith('My Movie', true);
  });

  it('will not submit a title that changes nothing', async () => {
    suggestItemTitles.mockResolvedValue({
      current: 'My.movie.2012.1080p', matched: null, reason: 'no_id',
    });
    renderModal();

    await waitFor(() => expect(screen.getByText(/never matched it/)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Rename' })).toBeDisabled();
  });

  it('passes the regenerate choice through, trimmed of stray whitespace', async () => {
    renderModal();
    await waitFor(() => expect(field().value).toBe('My Movie'));

    fireEvent.change(field(), { target: { value: '  My Movie  ' } });
    fireEvent.click(screen.getByLabelText(/Regenerate the poster/));
    fireEvent.click(screen.getByRole('button', { name: 'Rename' }));

    expect(onConfirm).toHaveBeenCalledWith('My Movie', false);
  });
});
