import type { TitleCheckProgress, TitleProposal } from '../../types';

export function initialSelection(proposals: TitleProposal[]): Set<number> {
  return new Set(proposals.filter(isPending).map((proposal) => proposal.item_id));
}

export function isPending(proposal: TitleProposal): boolean {
  return proposal.status === 'pending';
}

export function toggle(selected: Set<number>, itemId: number): Set<number> {
  const next = new Set(selected);
  if (!next.delete(itemId)) next.add(itemId);
  return next;
}

export function toggleAll(proposals: TitleProposal[], selected: Set<number>): Set<number> {
  return selected.size === pendingCount(proposals)
    ? new Set()
    : initialSelection(proposals);
}

export function pendingCount(proposals: TitleProposal[]): number {
  return proposals.filter(isPending).length;
}

export function approveLabel(count: number): string {
  if (count === 0) return 'Rename';
  return count === 1 ? 'Rename 1 item' : `Rename ${count} items`;
}

export function summaryLine(proposals: TitleProposal[], libraryName: string): string {
  const pending = pendingCount(proposals);
  if (pending === 0) {
    return `No titles in ${libraryName} disagree with the catalogue your media server matched them to.`;
  }
  const subject = pending === 1 ? '1 title' : `${pending} titles`;
  return `${subject} in ${libraryName} disagree with the catalogue your media server matched them to.`;
}

export function runSummary(proposals: TitleProposal[]): string | null {
  const renamed = proposals.filter((proposal) => proposal.status === 'renamed').length;
  const failed = proposals.filter((proposal) => proposal.status === 'failed').length;
  if (!renamed && !failed) return null;

  const parts = [`${renamed} renamed`];
  if (failed) parts.push(`${failed} could not be`);
  return parts.join(', ');
}

export function checkProgressLine(check: TitleCheckProgress): string | null {
  if (!check.running) return null;
  const found = check.mismatched === 1 ? '1 to fix' : `${check.mismatched} to fix`;
  return `Checking ${check.checked} of ${check.total} — ${found} so far`;
}

export function checkFraction(check: TitleCheckProgress): number {
  return check.total > 0 ? Math.min(check.checked / check.total, 1) : 0;
}
