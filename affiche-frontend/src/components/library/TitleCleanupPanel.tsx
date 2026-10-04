import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowRight, Check, Loader2, SearchCheck } from 'lucide-react';

import { errorMessage, libraryApi } from '../../api';
import { useToast } from '../../context/ToastContext';
import type { TitleCheckProgress, TitleProposal } from '../../types';
import { Modal } from '../common';
import {
  approveLabel, checkFraction, checkProgressLine, initialSelection, isPending, pendingCount,
  runSummary, summaryLine, toggle, toggleAll,
} from './titleCleanup';
import styles from './TitleCleanupPanel.module.css';

interface TitleCleanupPanelProps {
  mediaServerId: number;
  libraryId: number;

  libraryName: string;

  mediaServerName?: string;

  onStarted: (taskId: string) => void;
  onClose: () => void;
}

export function TitleCleanupPanel({
  mediaServerId,
  libraryId,
  libraryName,
  mediaServerName,
  onStarted,
  onClose,
}: TitleCleanupPanelProps) {
  const toast = useToast();
  const [proposals, setProposals] = useState<TitleProposal[] | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [regenerate, setRegenerate] = useState(true);
  const [isApplying, setIsApplying] = useState(false);
  const [check, setCheck] = useState<TitleCheckProgress>(
    { running: false, checked: 0, total: 0, mismatched: 0 });
  const [isStartingCheck, setIsStartingCheck] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const load = async () => {
      try {
        const state = await libraryApi.getTitleCleanupState(mediaServerId, libraryId);
        if (cancelled) return;
        setProposals((previous) => {

          setSelected((current) => (previous === null
            ? initialSelection(state.proposals)
            : withNewRowsSelected(current, previous, state.proposals)));
          return state.proposals;
        });
        setCheck(state.check);
        if (state.check.running) timer = setTimeout(load, POLL_MS);
      } catch (error) {
        if (cancelled) return;
        setProposals((previous) => previous ?? []);
        toast.error(errorMessage(error, 'Could not load the proposed renames.'),
          { title: 'Clean up titles' });
      }
    };
    load();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [mediaServerId, libraryId, toast]);

  const startCheck = async () => {
    setIsStartingCheck(true);
    try {
      await libraryApi.checkLibraryTitles(mediaServerId, libraryId);

      setCheck({ running: true, checked: 0, total: 0, mismatched: 0 });
      pollUntilIdle();
    } catch (error) {
      toast.error(errorMessage(error, 'Could not start the check.'), { title: 'Clean up titles' });
    } finally {
      setIsStartingCheck(false);
    }
  };

  const pollUntilIdle = async () => {
    try {
      const state = await libraryApi.getTitleCleanupState(mediaServerId, libraryId);
      setProposals((previous) => {
        setSelected((current) => (previous === null
          ? initialSelection(state.proposals)
          : withNewRowsSelected(current, previous, state.proposals)));
        return state.proposals;
      });
      setCheck(state.check);
      if (state.check.running) setTimeout(pollUntilIdle, POLL_MS);
    } catch {}
  };

  const apply = async () => {
    setIsApplying(true);
    try {
      const task = await libraryApi.applyTitleCleanup(
        mediaServerId, libraryId, [...selected], regenerate);
      onStarted(task.task_id);
      onClose();
    } catch (error) {
      toast.error(errorMessage(error, 'Could not start the renames.'),
        { title: 'Clean up titles' });
      setIsApplying(false);
    }
  };

  const rows = proposals ?? [];
  const pending = pendingCount(rows);
  const finished = runSummary(rows);
  const progressLine = checkProgressLine(check);
  const serverName = mediaServerName || 'your media server';

  return (
    <Modal
      size="drawer"
      label="Clean up titles"
      title="Clean up titles"
      description={
        proposals === null ? 'Loading…' : (
          <>
            {summaryLine(rows, libraryName)}
            {pending > 0 && (
              <> Approving renames them on <strong>{serverName}</strong> and locks the field. Files
                on disk are not touched.</>
            )}
          </>
        )
      }
      isBusy={isApplying}
      onClose={onClose}
      footer={
        <>
          {finished && <span className={styles.footerNote}>{finished}</span>}
          <button className={styles.secondary} onClick={onClose} disabled={isApplying}>
            Close
          </button>
          <button
            className={styles.primary}
            onClick={apply}
            disabled={isApplying || selected.size === 0}
          >
            {isApplying ? <Loader2 size={16} className="spin" /> : null}
            {approveLabel(selected.size)}
          </button>
        </>
      }
    >
      <div className={styles.content}>
        <div className={styles.toolbar}>
          <button
            className={styles.checkButton}
            onClick={startCheck}
            disabled={check.running || isStartingCheck || isApplying}
          >
            {check.running || isStartingCheck
              ? <Loader2 size={15} className="spin" />
              : <SearchCheck size={15} />}
            Check titles
          </button>
          {progressLine && <span className={styles.progressLine}>{progressLine}</span>}
        </div>
        {check.running && (
          <div className={styles.progressTrack} role="progressbar"
               aria-valuenow={Math.round(checkFraction(check) * 100)}
               aria-valuemin={0} aria-valuemax={100} aria-label="Checking titles">
            <div className={styles.progressBar}
                 style={{ width: `${checkFraction(check) * 100}%` }} />
          </div>
        )}
        {proposals === null ? (
          <div className={styles.loading}>
            <Loader2 size={18} className="spin" aria-hidden="true" />
            Loading proposed renames…
          </div>
        ) : rows.length === 0 ? (
          <p className={styles.empty}>
            {check.running
              ? 'Checking every title against the catalogue. Anything that disagrees will appear here.'
              : 'Nothing to review. Titles are checked at the end of every sync — press Check titles '
                + 'to look again now.'}
          </p>
        ) : (
          <>
            {pending > 0 && (
              <label className={styles.selectAll}>
                <input
                  type="checkbox"
                  checked={selected.size === pending}

                  ref={(node) => {
                    if (node) node.indeterminate = selected.size > 0 && selected.size < pending;
                  }}
                  onChange={() => setSelected(toggleAll(rows, selected))}
                  disabled={isApplying}

                  aria-label="Select all"
                />
                <span>Select all</span>
                <span className={styles.selectCount}>{selected.size}/{pending}</span>
              </label>
            )}

            <ul className={styles.list}>
              {rows.map((proposal) => (
                <li key={proposal.item_id} className={styles.row}>
                  <label className={styles.rowMain}>
                    {isPending(proposal) ? (
                      <input
                        type="checkbox"
                        checked={selected.has(proposal.item_id)}
                        onChange={() => setSelected(toggle(selected, proposal.item_id))}
                        disabled={isApplying}
                        aria-label={`Rename ${proposal.current_title}`}
                      />
                    ) : (
                      <StatusIcon status={proposal.status} />
                    )}
                    <span className={styles.titles}>
                      <span className={styles.current}>{proposal.current_title}</span>
                      <span className={styles.proposed}>
                        <ArrowRight size={13} aria-hidden="true" />
                        {proposal.proposed_title}
                      </span>
                    </span>
                    {proposal.provider && (
                      <span className={styles.provider}>{proposal.provider.toUpperCase()}</span>
                    )}
                  </label>
                  {proposal.error && <p className={styles.rowError}>{proposal.error}</p>}
                </li>
              ))}
            </ul>

            {pending > 0 && (
              <label className={styles.checkbox}>
                <input
                  type="checkbox"
                  checked={regenerate}
                  onChange={(e) => setRegenerate(e.target.checked)}
                  disabled={isApplying}
                />
                <span>
                  Regenerate posters afterwards
                  <span className={styles.checkboxNote}>
                    Posters carry the old title until they are drawn again.
                  </span>
                </span>
              </label>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}

const POLL_MS = 1500;

function withNewRowsSelected(
  current: Set<number>,
  previous: TitleProposal[],
  next: TitleProposal[]
): Set<number> {
  const known = new Set(previous.map((proposal) => proposal.item_id));
  const updated = new Set(current);
  for (const proposal of next) {
    if (!known.has(proposal.item_id) && isPending(proposal)) updated.add(proposal.item_id);
  }

  for (const proposal of next) {
    if (!isPending(proposal)) updated.delete(proposal.item_id);
  }
  return updated;
}

function StatusIcon({ status }: { status: TitleProposal['status'] }) {
  return status === 'renamed' ? (
    <Check size={16} className={styles.renamed} aria-label="Renamed" />
  ) : (
    <AlertTriangle size={16} className={styles.failed} aria-label="Could not rename" />
  );
}
