import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { TitleCleanupPanel } from './TitleCleanupPanel';
import { libraryApi } from '../../api';
import type { TitleProposal } from '../../types';

vi.mock('../../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api')>();
  return {
    ...actual,
    libraryApi: {
      ...actual.libraryApi,
      getTitleCleanupState: vi.fn(),
      applyTitleCleanup: vi.fn(),
      checkLibraryTitles: vi.fn(),
    },
  };
});

const toast = { error: vi.fn(), success: vi.fn(), info: vi.fn(), show: vi.fn() };
vi.mock('../../context/ToastContext', () => ({ useToast: () => toast }));

const getTitleCleanupState = vi.mocked(libraryApi.getTitleCleanupState);
const applyTitleCleanup = vi.mocked(libraryApi.applyTitleCleanup);
const checkLibraryTitles = vi.mocked(libraryApi.checkLibraryTitles);

const idle = { running: false, checked: 0, total: 0, mismatched: 0 };
const state = (proposals: TitleProposal[], check = idle) => ({ proposals, check });

const row = (item_id: number, overrides: Partial<TitleProposal> = {}): TitleProposal => ({
  item_id,
  current_title: `My.movie.${item_id}.1080p`,
  proposed_title: `My Movie ${item_id}`,
  provider: 'tmdb',
  status: 'pending',
  ...overrides,
});

const onStarted = vi.fn();
const onClose = vi.fn();

const renderPanel = () =>
  render(
    <TitleCleanupPanel
      mediaServerId={1}
      libraryId={3}
      libraryName="Films FR"
      mediaServerName="Plex"
      onStarted={onStarted}
      onClose={onClose}
    />
  );

const approve = () => screen.getByRole('button', { name: /^Rename/ });

beforeEach(() => {
  vi.clearAllMocks();
  getTitleCleanupState.mockResolvedValue(state([row(1), row(2), row(3)]));
  applyTitleCleanup.mockResolvedValue({ task_id: 'task-1', status: 'running', message: '' });
  checkLibraryTitles.mockResolvedValue({ task_id: 'check-1', status: 'running', message: '' });
});

describe('TitleCleanupPanel', () => {
  it('lists every proposed rename with both titles', async () => {
    renderPanel();

    await waitFor(() => expect(screen.getByText('My.movie.1.1080p')).toBeInTheDocument());
    expect(screen.getByText('My Movie 1')).toBeInTheDocument();
    expect(screen.getByText(/3 titles in Films FR/)).toBeInTheDocument();
  });

  it('starts with every row ticked, and counts them on the button', async () => {
    renderPanel();

    await waitFor(() => expect(approve()).toHaveTextContent('Rename 3 items'));
  });

  it('submits only the rows still ticked', async () => {
    renderPanel();
    await waitFor(() => expect(approve()).toHaveTextContent('Rename 3 items'));

    fireEvent.click(screen.getByLabelText('Rename My.movie.2.1080p'));
    expect(approve()).toHaveTextContent('Rename 2 items');
    fireEvent.click(approve());

    await waitFor(() => expect(applyTitleCleanup).toHaveBeenCalledWith(1, 3, [1, 3], true));
  });

  it('passes the regenerate choice through', async () => {
    renderPanel();
    await waitFor(() => expect(approve()).toHaveTextContent('Rename 3 items'));

    fireEvent.click(screen.getByLabelText(/Regenerate posters/));
    fireEvent.click(approve());

    await waitFor(() =>
      expect(applyTitleCleanup).toHaveBeenCalledWith(1, 3, [1, 2, 3], false));
  });

  it('cannot approve once every row is unticked', async () => {
    renderPanel();
    await waitFor(() => expect(approve()).toHaveTextContent('Rename 3 items'));

    fireEvent.click(screen.getByLabelText('Select all'));

    expect(approve()).toBeDisabled();
  });

  it('hands the task id back and closes, rather than blocking on the run', async () => {
    renderPanel();
    await waitFor(() => expect(approve()).toHaveTextContent('Rename 3 items'));

    fireEvent.click(approve());

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith('task-1'));
    expect(onClose).toHaveBeenCalled();
  });

  it('shows a reopened run’s finished rows with their outcome, not as work to approve', async () => {
    getTitleCleanupState.mockResolvedValue(state([
      row(1, { status: 'renamed' }),
      row(2, { status: 'failed', error: 'Plex would not.' }),
      row(3),
    ]));
    renderPanel();

    await waitFor(() => expect(screen.getByLabelText('Renamed')).toBeInTheDocument());
    expect(screen.getByLabelText('Could not rename')).toBeInTheDocument();
    expect(screen.getByText('Plex would not.')).toBeInTheDocument();

    expect(approve()).toHaveTextContent('Rename 1 item');
  });

  it('says plainly when there is nothing to review', async () => {
    getTitleCleanupState.mockResolvedValue(state([]));
    renderPanel();

    await waitFor(() => expect(screen.getByText(/Nothing to review/)).toBeInTheDocument());
    expect(approve()).toBeDisabled();
  });

  it('never applies anything just by opening', async () => {
    renderPanel();

    await waitFor(() => expect(getTitleCleanupState).toHaveBeenCalled());
    expect(applyTitleCleanup).not.toHaveBeenCalled();
  });

  it('starts a check when asked, and shows it running', async () => {
    getTitleCleanupState.mockResolvedValue(state([]));
    renderPanel();
    await waitFor(() => expect(screen.getByText(/Nothing to review/)).toBeInTheDocument());

    getTitleCleanupState.mockResolvedValue(
      state([], { running: true, checked: 12, total: 40, mismatched: 2 }));
    fireEvent.click(screen.getByRole('button', { name: /Check titles/ }));

    await waitFor(() => expect(checkLibraryTitles).toHaveBeenCalledWith(1, 3));
    await waitFor(() =>
      expect(screen.getByText(/Checking 12 of 40 — 2 to fix so far/)).toBeInTheDocument());
  });

  it('ticks rows that appear mid-check but keeps an opt-out already made', async () => {
    renderPanel();
    await waitFor(() => expect(approve()).toHaveTextContent('Rename 3 items'));

    fireEvent.click(screen.getByLabelText('Rename My.movie.2.1080p'));
    expect(approve()).toHaveTextContent('Rename 2 items');

    getTitleCleanupState.mockResolvedValue(
      state([row(1), row(2), row(3), row(4)], { running: true, checked: 4, total: 4, mismatched: 4 }));
    fireEvent.click(screen.getByRole('button', { name: /Check titles/ }));

    await waitFor(() => expect(approve()).toHaveTextContent('Rename 3 items'));
    fireEvent.click(approve());
    await waitFor(() => expect(applyTitleCleanup).toHaveBeenCalledWith(1, 3, [1, 3, 4], true));
  });

  it('cannot start a second check while one is running', async () => {
    getTitleCleanupState.mockResolvedValue(
      state([], { running: true, checked: 1, total: 9, mismatched: 0 }));
    renderPanel();

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Check titles/ })).toBeDisabled());
  });

  it('reports a failure to load rather than showing an empty list as success', async () => {
    getTitleCleanupState.mockRejectedValue(new Error('down'));
    renderPanel();

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(screen.getByText(/Nothing to review/)).toBeInTheDocument();
  });
});
