import type { TaskKind, TaskProgressState } from '../types';

export interface TaskSummary {
  title: string;
  message: string;

  offerFailed: boolean;
}

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`;

export function taskSummary(kind: TaskKind, scopeName: string, failedCount?: number): TaskSummary {
  switch (kind) {
    case 'generate': {
      const failed = failedCount ?? 0;
      return {
        title: 'Posters generated',
        message: failed > 0
          ? `Finished ${scopeName}. ${plural(failed, 'item')} failed; each one says why.`
          : `Finished ${scopeName}.`,
        offerFailed: failed > 0,
      };
    }
    case 'upload':
      return { title: 'Posters uploaded', message: `${scopeName} is up to date on the media server.`, offerFailed: false };
    case 'sync':
      return { title: 'Library synced', message: `${scopeName} is up to date with the media server.`, offerFailed: false };
    case 'reset':
      return { title: 'Posters reset', message: `${scopeName} shows its original artwork again.`, offerFailed: false };
    case 'other':
      return { title: 'Task finished', message: `Finished working on ${scopeName}.`, offerFailed: false };
  }
}

export function progressPercent(progress: TaskProgressState | null | undefined): number {
  if (!progress || progress.total <= 0) return 0;
  return Math.min(100, Math.round((progress.current / progress.total) * 100));
}
