import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';

import { ProviderHistoryChart } from './ProviderHistoryChart';
import { toIsoDay } from '../../pages/providerHistory';
import type { ProviderHistory } from '../../types';

const today = toIsoDay(new Date());
const yesterday = toIsoDay(new Date(Date.now() - 86_400_000));

const history = (series: ProviderHistory['series']): ProviderHistory => ({
  days: 30,
  series,
  totals: [],
});

function renderChart(props: Partial<React.ComponentProps<typeof ProviderHistoryChart>> = {}) {
  return render(
    <ProviderHistoryChart
      history={history([
        { day: yesterday, provider: 'tmdb', count: 4 },
        { day: today, provider: 'tmdb', count: 2 },
        { day: today, provider: 'fanart', count: 1 },
      ])}
      days={30}
      onDaysChange={vi.fn()}
      isLoading={false}
      isRefreshing={false}
      error={null}
      {...props}
    />
  );
}

const legend = () => screen.getByRole('list');

describe('ProviderHistoryChart', () => {
  it('names every series, which is what makes the palette legal', () => {
    renderChart();

    expect(within(legend()).getByText('TMDB')).toBeInTheDocument();
    expect(within(legend()).getByText('Fanart.tv')).toBeInTheDocument();
  });

  it('shows each provider window total, ranked with the largest first', () => {
    renderChart();

    const names = within(legend())
      .getAllByRole('listitem')
      .map((row) => row.textContent);
    expect(names[0]).toContain('TMDB');
    expect(names[0]).toContain('6');
    expect(names[1]).toContain('Fanart.tv');
  });

  it('describes the chart for a reader who cannot see it', () => {
    renderChart();

    expect(screen.getByRole('img', { name: /last 30 days/i })).toBeInTheDocument();
  });

  it('offers the window presets, marking the current one', () => {
    renderChart({ days: 7 });

    expect(screen.getByRole('button', { name: '7 days' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '30 days' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('changes the window when a preset is chosen', () => {
    const onDaysChange = vi.fn();
    renderChart({ onDaysChange });

    fireEvent.click(screen.getByRole('button', { name: '90 days' }));

    expect(onDaysChange).toHaveBeenCalledWith(90);
  });

  it('reads out one day at a time from the keyboard', () => {

    renderChart();
    const plot = screen.getByRole('img', { name: /last 30 days/i });

    fireEvent.keyDown(plot, { key: 'ArrowLeft' });

    const rows = within(legend()).getAllByRole('listitem');
    expect(rows[0].textContent).toContain('4');
    expect(rows[1].textContent).toContain('0');
  });

  it('goes back to the window totals when focus leaves', () => {
    renderChart();
    const plot = screen.getByRole('img', { name: /last 30 days/i });

    fireEvent.keyDown(plot, { key: 'ArrowLeft' });
    fireEvent.blur(plot);

    expect(within(legend()).getAllByRole('listitem')[0].textContent).toContain('6');
  });

  it('ignores a key that is not a step', () => {
    renderChart();
    const plot = screen.getByRole('img', { name: /last 30 days/i });

    fireEvent.keyDown(plot, { key: 'a' });

    expect(within(legend()).getAllByRole('listitem')[0].textContent).toContain('6');
  });

  it('says so when nothing was generated, rather than drawing an empty grid', () => {
    renderChart({ history: history([]) });

    expect(screen.getByText(/No posters generated in the last 30 days/i)).toBeInTheDocument();
  });

  it('explains that the counter starts at install', () => {

    renderChart();

    expect(screen.getByText(/starts from the day this was installed/i)).toBeInTheDocument();
  });

  it('surfaces a failure instead of an empty chart', () => {
    renderChart({ error: 'Request failed: 500' });

    expect(screen.getByRole('alert')).toHaveTextContent('Request failed: 500');
  });

  it('keeps the chart on screen while a new window loads', () => {

    renderChart({ isRefreshing: true });

    expect(screen.getByRole('img', { name: /last 30 days/i })).toBeInTheDocument();
    expect(within(legend()).getByText('TMDB')).toBeInTheDocument();
  });
});
