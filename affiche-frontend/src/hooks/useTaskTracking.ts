import { useCallback, useEffect, useRef, useState } from 'react';
import { tasksApi } from '../api';
import { useToast } from '../context/ToastContext';
import type { TaskKind, TaskProgressState } from '../types';

export function taskKindFromName(name?: string): TaskKind {
  if (name?.startsWith('library_sync')) return 'sync';
  if (name?.startsWith('poster_sync')) return 'generate';
  if (name?.startsWith('poster_reset')) return 'reset';
  return 'other';
}

interface UseTaskTrackingOptions {

  onTaskFinished: () => void;
}

export function useTaskTracking({ onTaskFinished }: UseTaskTrackingOptions) {
  const toast = useToast();
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [taskMessage, setTaskMessage] = useState<string | null>(null);
  const [taskKind, setTaskKind] = useState<TaskKind | null>(null);
  const [taskProgress, setTaskProgress] = useState<TaskProgressState | null>(null);

  const currentTaskIdRef = useRef<string | null>(null);

  const startTaskTracking = useCallback((taskId: string, message?: string, kind: TaskKind = 'other') => {
    currentTaskIdRef.current = taskId;
    setIsActionLoading(true);
    setTaskMessage(message || 'Starting task...');
    setTaskKind(kind);
    setTaskProgress(null);
  }, []);

  const attachRunningTask = useCallback(async () => {
    try {
      const task = await tasksApi.getRunningBlockingTask();
      if (!task || (task.status !== 'pending' && task.status !== 'running')) return;

      startTaskTracking(task.task_id, task.message, taskKindFromName(task.task_name));
      if (task.progress) {
        setTaskProgress({
          current: task.progress.current,
          total: task.progress.total,
          message: task.progress.message ?? undefined,
        });
      }
    } catch (error) {
      console.error('Failed to check for running tasks:', error);
    }
  }, [startTaskTracking]);

  const initialCheckDoneRef = useRef(false);
  useEffect(() => {
    if (initialCheckDoneRef.current) return;
    initialCheckDoneRef.current = true;

    const checkRunningTask = async () => { await attachRunningTask(); };
    checkRunningTask();
  }, [attachRunningTask]);

  const handleTaskStatus = useCallback(
    (taskId: string, status: string, taskName: string, message?: string, error?: string) => {
      if (currentTaskIdRef.current !== taskId) return;

      setTaskMessage(message || `Task ${status}...`);
      setTaskKind((prev) => prev ?? taskKindFromName(taskName));

      if (status !== 'completed' && status !== 'failed' && status !== 'cancelled') return;

      currentTaskIdRef.current = null;
      setIsActionLoading(false);
      setTaskMessage(null);
      setTaskKind(null);
      setTaskProgress(null);

      if (status === 'failed') {
        console.error('Task failed:', error);
        toast.error(error || 'Unknown error', { title: 'Task failed' });
      }

      onTaskFinished();
    },
    [onTaskFinished, toast]
  );

  const handleTaskProgress = useCallback(
    (taskId: string, taskName: string, current: number, total: number, message?: string) => {
      if (currentTaskIdRef.current !== taskId) return;
      setTaskProgress({ current, total, message: message ?? undefined });
      setTaskKind((prev) => prev ?? taskKindFromName(taskName));
      if (message) setTaskMessage(message);
    },
    []
  );

  const stopTask = useCallback(async () => {
    if (!currentTaskIdRef.current) return;
    try {
      await tasksApi.cancelTask(currentTaskIdRef.current);
    } catch (error) {
      console.error('Failed to stop task:', error);
    }
  }, []);

  return {
    isActionLoading,
    setIsActionLoading,
    taskMessage,
    setTaskMessage,
    taskKind,
    taskProgress,
    startTaskTracking,
    attachRunningTask,
    handleTaskStatus,
    handleTaskProgress,
    stopTask,
  };
}
