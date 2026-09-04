import { providerLabel } from '../../constants/providers';
import type { LibraryItem } from '../../types';
import { errorCauseCopy } from './errorCause';

export function posterSource(provider?: string | null): string {
  if (!provider) return '—';
  if (provider === 'server') return 'Media server artwork';
  if (provider === 'manual') return 'Chosen manually';
  return providerLabel(provider);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

export function formatDate(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export function posterStatus(item: LibraryItem): string {
  if (item.poster_uploaded_at) return `Uploaded ${formatDateTime(item.poster_uploaded_at)}`;
  if (item.processed || item.has_poster) return 'Generated (not uploaded)';
  return 'None';
}

export function canReset(item: LibraryItem): boolean {
  return item.processed || !!item.error_message;
}

export function failureTooltip(item: LibraryItem): string | undefined {
  if (!item.error_message) return undefined;
  const cause = errorCauseCopy(item);
  return cause ? `${item.error_message}

${cause.summary}` : item.error_message;
}

export function hasQuality(item: LibraryItem): boolean {
  return !!(item.media_resolution || item.media_height || item.video_codec ||
    item.media_container || item.media_size_bytes);
}

export function formatFileSize(bytes?: number | null): string {
  if (!bytes) return '—';
  const gb = bytes / 1024 ** 3;
  if (gb >= 1) return `${gb.toFixed(2)} GB`;
  return `${(bytes / 1024 ** 2).toFixed(0)} MB`;
}

export function formatBitrate(bps?: number | null): string {
  if (!bps) return '—';
  return `${(bps / 1_000_000).toFixed(1)} Mbps`;
}

export function formatChannels(channels?: number | null): string | null {
  if (!channels) return null;
  const map: Record<number, string> = { 1: '1.0', 2: '2.0', 6: '5.1', 7: '6.1', 8: '7.1' };
  return map[channels] ?? `${channels}ch`;
}

export function formatAudio(item: LibraryItem): string {
  const parts = [item.audio_codec?.toUpperCase(), formatChannels(item.audio_channels)].filter(Boolean);
  return parts.length ? parts.join(' · ') : '—';
}
