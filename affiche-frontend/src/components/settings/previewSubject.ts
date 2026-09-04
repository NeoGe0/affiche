import { posterTargetFromItem, type PosterTarget } from '../library/posterTarget';
import type { Library, LibraryItem } from '../../types';

export interface PreviewSubject extends PosterTarget {
  libraryId: number;
  itemId: number;
}

export function previewSubjectFromItem(item: LibraryItem): PreviewSubject {
  return {
    ...posterTargetFromItem(item),
    libraryId: item.library_id,
    itemId: item.id,
  };
}

export interface LibraryOption {
  id: number;
  mediaServerId: number;
  label: string;
}

export function libraryOptions(
  servers: { id: number; name: string }[],
  libraries: Library[]
): LibraryOption[] {
  const serverNames = new Map(servers.map((server) => [server.id, server.name]));
  const qualify = servers.length > 1;

  return libraries.flatMap((library) => {
    const serverName = serverNames.get(library.media_server_id);
    if (serverName === undefined) return [];
    return [
      {
        id: library.id,
        mediaServerId: library.media_server_id,
        label: qualify ? `${serverName} · ${library.name}` : library.name,
      },
    ];
  });
}

export function serializePreviewSubject(subject: PreviewSubject): string {
  return JSON.stringify(subject);
}

export function parsePreviewSubject(raw: string | null): PreviewSubject | null {
  if (!raw) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  if (typeof parsed !== 'object' || parsed === null) return null;
  const value = parsed as Record<string, unknown>;

  const { libraryId, itemId, title, mediaType } = value;
  if (typeof libraryId !== 'number' || typeof itemId !== 'number') return null;
  if (typeof title !== 'string' || title === '') return null;
  if (mediaType !== 'movie' && mediaType !== 'show') return null;

  const optionalNumber = (candidate: unknown): number | undefined =>
    typeof candidate === 'number' && Number.isFinite(candidate) ? candidate : undefined;

  return {
    libraryId,
    itemId,
    title,
    mediaType,
    year: optionalNumber(value.year),
    tmdbId: optionalNumber(value.tmdbId),
    tvdbId: optionalNumber(value.tvdbId),
  };
}
