import type { LibraryItem } from '../../types';
import { formatAudio, formatFileSize, hasQuality } from './format';

export type PosterState = 'failed' | 'uploaded' | 'ready' | 'pending';

export function posterState(item: LibraryItem): PosterState {
  if (item.error_message) return 'failed';
  if (item.poster_uploaded_at) return 'uploaded';
  if (item.processed) return 'ready';
  return 'pending';
}

export const POSTER_STATE_LABEL: Record<PosterState, string> = {
  failed: 'Failed',
  uploaded: 'On server',
  ready: 'Ready to upload',
  pending: 'No poster yet',
};

export type PrimaryPosterAction = 'upload' | 'generate' | 'choose';

export function primaryPosterAction(item: LibraryItem): PrimaryPosterAction | null {
  switch (posterState(item)) {
    case 'failed':
      return 'choose';
    case 'ready':
      return 'upload';
    case 'pending':
      return item.locked ? null : 'generate';
    case 'uploaded':
      return null;
  }
}

export function detailsSummary(item: LibraryItem): string {
  if (!hasQuality(item)) return 'IDs and dates';
  const resolution = item.media_resolution || (item.media_height ? `${item.media_height}p` : null);
  const audio = formatAudio(item);
  return [
    resolution,
    item.video_codec?.toUpperCase(),
    audio === '—' ? null : audio,
    item.media_container?.toUpperCase(),
    item.media_size_bytes ? formatFileSize(item.media_size_bytes) : null,
  ].filter(Boolean).join(' · ');
}
