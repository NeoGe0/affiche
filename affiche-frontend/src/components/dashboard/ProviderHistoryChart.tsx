import { useState } from 'react';

import { posterSource } from '../library/format';
import {
  labelledDays,
  linePath,
  nearestIndex,
  shortDay,
  toSeries,
  windowDays,
  xAt,
  yAt,
  yMax,
  yTicks,
  type PlotBox,
} from '../../pages/providerHistory';
import { useElementWidth, WINDOW_PRESETS } from '../../hooks';
import type { ProviderHistory } from '../../types';
import styles from './ProviderHistoryChart.module.css';

const PLOT_HEIGHT = 200;

const PADDING = { left: 34, right: 8, top: 8, bottom: 22 };

const FALLBACK_WIDTH = 720;

const MIN_PLOT_WIDTH = 320;

const SERIES_SLOTS = 8;

interface ProviderHistoryChartProps {
  history: ProviderHistory | null;
  days: number;
  onDaysChange: (days: number) => void;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
}

export function ProviderHistoryChart({
  history,
  days,
  onDaysChange,
  isLoading,
  isRefreshing,
  error,
}: ProviderHistoryChartProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const { ref: plotRef, width: measured } = useElementWidth<HTMLDivElement>(FALLBACK_WIDTH);
  const box: PlotBox = {
    width: Math.max(measured - PADDING.left - PADDING.right, MIN_PLOT_WIDTH),
    height: PLOT_HEIGHT,
  };

  const dayLabels = windowDays(days);
  const series = toSeries(history?.series ?? [], dayLabels);
  const max = yMax(series);
  const labelled = labelledDays(dayLabels.length);
  const isEmpty = series.length === 0;

  const handlePointer = (event: React.PointerEvent<SVGSVGElement>) => {

    const rect = event.currentTarget.getBoundingClientRect();
    setHovered(nearestIndex(event.clientX - rect.left - PADDING.left, dayLabels.length, box));
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {

    const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    setHovered((current) => {
      const next = (current ?? dayLabels.length - 1) + step;
      return Math.min(Math.max(next, 0), dayLabels.length - 1);
    });
  };

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Where posters came from</h2>
          <p className={styles.hint}>
            Posters stored per provider, by day. Counted as they are generated, so it starts from
            the day this was installed rather than from your library's history.
          </p>
        </div>
        <div className={styles.ranges} role="group" aria-label="Time range">
          {WINDOW_PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              className={`${styles.range} ${preset === days ? styles.rangeActive : ''}`}
              onClick={() => onDaysChange(preset)}
              aria-pressed={preset === days}
            >
              {preset} days
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <p className={styles.message} role="alert">{error}</p>
      ) : isLoading ? (
        <p className={styles.message}>Loading…</p>
      ) : isEmpty ? (
        <p className={styles.message}>
          No posters generated in the last {days} days.
        </p>
      ) : (
        <div className={`${styles.body} ${isRefreshing ? styles.refreshing : ''}`}>
          {
}
          <div className={styles.plot} ref={plotRef}>
          <svg
            className={styles.chart}
            width={box.width + PADDING.left + PADDING.right}
            height={box.height + PADDING.top + PADDING.bottom}
            viewBox={`0 0 ${box.width + PADDING.left + PADDING.right} ${box.height + PADDING.top + PADDING.bottom}`}
            role="img"
            aria-label={`Posters per provider over the last ${days} days. The figures are listed after the chart.`}
            tabIndex={0}
            onPointerMove={handlePointer}
            onPointerLeave={() => setHovered(null)}
            onKeyDown={handleKeyDown}
            onBlur={() => setHovered(null)}
          >
            <g transform={`translate(${PADDING.left} ${PADDING.top})`}>
              {yTicks(max).map((tick) => {
                const y = yAt(tick, max, box);
                return (
                  <g key={tick}>
                    <line className={styles.grid} x1={0} x2={box.width} y1={y} y2={y} />
                    <text className={styles.axisLabel} x={-8} y={y} dominantBaseline="middle" textAnchor="end">
                      {tick}
                    </text>
                  </g>
                );
              })}

              {dayLabels.map((day, index) =>
                labelled.has(index) ? (
                  <text
                    key={day}
                    className={styles.axisLabel}
                    x={xAt(index, dayLabels.length, box)}
                    y={box.height + 16}
                    textAnchor="middle"
                  >
                    {shortDay(day)}
                  </text>
                ) : null
              )}

              {hovered !== null && (
                <line
                  className={styles.crosshair}
                  x1={xAt(hovered, dayLabels.length, box)}
                  x2={xAt(hovered, dayLabels.length, box)}
                  y1={0}
                  y2={box.height}
                />
              )}

              {series.map((line, index) => (
                <path
                  key={line.provider}
                  className={styles.line}
                  d={linePath(line.values, max, box)}
                  style={{ stroke: seriesColor(index) }}
                />
              ))}

              {hovered !== null &&
                series.map((line, index) => (
                  <circle
                    key={line.provider}
                    className={styles.point}
                    cx={xAt(hovered, dayLabels.length, box)}
                    cy={yAt(line.values[hovered], max, box)}
                    r={4}
                    style={{ fill: seriesColor(index) }}
                  />
                ))}
            </g>
          </svg>
          </div>

          {
}
          <ul className={styles.legend}>
            {series.map((line, index) => (
              <li key={line.provider} className={styles.legendRow}>
                <span className={styles.swatch} style={{ backgroundColor: seriesColor(index) }} />
                <span className={styles.legendName}>{posterSource(line.provider)}</span>
                <span className={styles.legendValue}>
                  {hovered === null ? line.total : line.values[hovered]}
                </span>
              </li>
            ))}
            <li className={styles.legendCaption}>
              {hovered === null ? `Total over ${days} days` : shortDay(dayLabels[hovered])}
            </li>
          </ul>
        </div>
      )}
    </section>
  );
}

function seriesColor(index: number): string {
  return `var(--series-${Math.min(index, SERIES_SLOTS - 1) + 1})`;
}
