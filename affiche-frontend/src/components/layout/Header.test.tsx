import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import { Header } from './Header';
import type { TaskKind } from '../../types';

const noop = vi.fn();

const renderHeader = (taskKind: TaskKind, progress = { current: 3, total: 12 }) =>
  render(
    <Header
      title="Films"
      onSyncLibrary={noop}
      onSyncPosters={noop}
      onResetPosters={noop}
      isLoading
      statusMessage="Resetting posters — Films"
      taskKind={taskKind}
      taskProgress={progress}
    />,
  );

describe('Header progress bar', () => {
  it('shows determinate progress while resetting', () => {
    renderHeader('reset');

    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '25');
  });

  it('shows determinate progress while generating', () => {
    renderHeader('generate');

    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '25');
  });

  it('leaves the bar out for a task that reports no progress', () => {
    renderHeader('other');

    expect(screen.queryByRole('progressbar')).toBeNull();
  });

  it('leaves the bar out when the total is unknown, rather than showing a stuck 0%', () => {
    renderHeader('reset', { current: 0, total: 0 });

    expect(screen.queryByRole('progressbar')).toBeNull();
  });

  it('replaces the status line with the bar, so progress is stated once', () => {
    renderHeader('reset');

    expect(screen.queryByText('Resetting posters — Films')).toBeNull();
  });

  it('keeps the status line for a task with no bar of its own', () => {
    renderHeader('other');

    expect(screen.getByText('Resetting posters — Films')).toBeTruthy();
  });
});
