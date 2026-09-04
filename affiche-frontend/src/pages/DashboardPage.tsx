import { AlertTriangle, CheckCircle, Image, Lock, RefreshCw, Upload } from 'lucide-react';

import { useDashboard, useEventStream, useProviderHistory } from '../hooks';
import { MediaServerIcon, LibraryTypeIcon } from '../components/common';
import { ProviderHistoryChart } from '../components/dashboard';
import { formatDateTime, posterSource } from '../components/library/format';
import type {
  DashboardLibrary, DashboardTask, ItemStats, MediaServerType, ProviderShare,
} from '../types';
import {
  byCoverageAscending, coveragePercent, providerBarPercent, taskLabel, taskTimestamp,
} from './dashboardStats';
import styles from './DashboardPage.module.css';

const NUMBER_FORMAT = new Intl.NumberFormat();

const format = (value: number) => NUMBER_FORMAT.format(value);

interface DashboardPageProps {

  onOpenLibrary: (mediaServerId: number, libraryId: number) => void;
}

export function DashboardPage({ onOpenLibrary }: DashboardPageProps) {
  const { summary, error, isLoading, reload } = useDashboard();
  const providerHistory = useProviderHistory();

  useEventStream({
    onTaskStatus: (_taskId, status) => {
      if (status !== 'running') {
        reload();

        providerHistory.reload();
      }
    },
    onLibrarySynced: () => reload(),
  });

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>Loading…</div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className={styles.page}>
        <div className={styles.error} role="alert">
          <AlertTriangle size={16} />
          {error}
        </div>
      </div>
    );
  }

  const { totals } = summary;
  const openLibrary = (row: DashboardLibrary) =>
    onOpenLibrary(row.media_server_id, row.library_id);

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Dashboard</h1>
            <p className={styles.subtitle}>
              {format(summary.library_count)} librar{summary.library_count === 1 ? 'y' : 'ies'} across{' '}
              {format(summary.media_server_count)} media server
              {summary.media_server_count === 1 ? '' : 's'}
            </p>
          </div>
          <button className={styles.refresh} onClick={reload} title="Refresh">
            <RefreshCw size={16} />
            Refresh
          </button>
        </header>

        <StatTiles totals={totals} />

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Libraries</h2>
          <p className={styles.sectionHint}>Least-covered first — this is the worklist.</p>
          {summary.libraries.length === 0 ? (
            <p className={styles.empty}>No libraries yet. Add a media server to get started.</p>
          ) : (
            <ul className={styles.libraries}>
              {byCoverageAscending(summary.libraries).map((row) => (
                <li key={row.library_id}>
                  <button className={styles.libraryRow} onClick={() => openLibrary(row)}>
                    <span className={styles.libraryName}>
                      <MediaServerIcon type={row.media_server_type as MediaServerType} size={14} />
                      <LibraryTypeIcon type={row.library_type} size={14} />
                      {row.library_name}
                      <span className={styles.libraryServer}>{row.media_server_name}</span>
                    </span>
                    <Coverage stats={row.stats} />
                    <span className={styles.libraryCounts}>
                      {row.stats.errors > 0 && (
                        <span className={styles.errorCount}>{format(row.stats.errors)} failed</span>
                      )}
                      {row.stats.locked > 0 && (
                        <span className={styles.lockedCount}>{format(row.stats.locked)} locked</span>
                      )}
                      <span className={styles.totalCount}>{format(row.stats.total)} items</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className={styles.section}>
          <ProviderHistoryChart
            history={providerHistory.history}
            days={providerHistory.days}
            onDaysChange={providerHistory.setDays}
            isLoading={providerHistory.isLoading}
            isRefreshing={providerHistory.isRefreshing}
            error={providerHistory.error}
          />
        </div>

        <div className={styles.columns}>
          <ProviderBreakdown providers={summary.providers} />
          <RecentActivity tasks={summary.recent_tasks} />
        </div>
      </div>
    </div>
  );
}

function StatTiles({ totals }: { totals: ItemStats }) {
  const tiles = [
    { label: 'Items', value: totals.total, icon: <Image size={16} />, tone: '' },
    { label: 'Posters generated', value: totals.processed, icon: <CheckCircle size={16} />, tone: styles.success },
    { label: 'Awaiting generation', value: totals.unprocessed, icon: <Image size={16} />, tone: '' },
    { label: 'Uploaded', value: totals.uploaded, icon: <Upload size={16} />, tone: '' },
    { label: 'Failed', value: totals.errors, icon: <AlertTriangle size={16} />, tone: styles.danger },
    { label: 'Locked', value: totals.locked, icon: <Lock size={16} />, tone: '' },
  ];

  return (
    <div className={styles.tiles}>
      {tiles.map((tile) => (
        <div key={tile.label} className={styles.tile}>
          <span className={`${styles.tileIcon} ${tile.tone}`}>{tile.icon}</span>
          <span className={styles.tileValue}>{format(tile.value)}</span>
          <span className={styles.tileLabel}>{tile.label}</span>
        </div>
      ))}
    </div>
  );
}

function Coverage({ stats }: { stats: ItemStats }) {
  const percent = coveragePercent(stats);
  return (
    <span className={styles.coverage}>
      <span
        className={styles.coverageTrack}
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Poster coverage"
      >
        <span className={styles.coverageFill} style={{ transform: `scaleX(${percent / 100})` }} />
      </span>
      <span className={styles.coverageValue}>{percent}%</span>
    </span>
  );
}

function ProviderBreakdown({ providers }: { providers: ProviderShare[] }) {
  const max = providers[0]?.count ?? 0;

  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>Poster sources</h2>
      <p className={styles.sectionHint}>
        Every poster you have now, by source — show, season and collection posters alike.
      </p>
      {providers.length === 0 ? (
        <p className={styles.empty}>
          No posters recorded yet. Posters generated before provenance tracking are not counted.
        </p>
      ) : (
        <ul className={styles.providers}>
          {providers.map(({ provider, count }) => (
            <li key={provider} className={styles.provider}>
              <span className={styles.providerName}>{posterSource(provider)}</span>
              <span className={styles.providerTrack}>
                <span
                  className={styles.providerFill}
                  style={{ width: `${providerBarPercent(count, max)}%` }}
                />
              </span>
              <span className={styles.providerCount}>{format(count)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RecentActivity({ tasks }: { tasks: DashboardTask[] }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>Recent activity</h2>
      <p className={styles.sectionHint}>Since the server last started.</p>
      {tasks.length === 0 ? (
        <p className={styles.empty}>Nothing has run yet.</p>
      ) : (
        <ul className={styles.tasks}>
          {tasks.map((task) => (
            <li key={task.task_id} className={styles.task}>
              <span className={`${styles.taskStatus} ${styles[task.status] ?? ''}`}>{task.status}</span>
              <span className={styles.taskName}>{taskLabel(task)}</span>
              <span className={styles.taskTime}>{formatDateTime(taskTimestamp(task))}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
