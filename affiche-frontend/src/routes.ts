import { matchPath } from 'react-router-dom';

export type AppView = 'library' | 'trash' | 'collections';

const VIEW_SEGMENT: Record<AppView, string> = {
  library: 'libraries',
  trash: 'trash',
  collections: 'collections',
};

export const ALL_LIBRARIES = 'all';

export interface AppLocation {
  serverId?: number;

  libraryId?: number;
  view: AppView;

  itemId?: number;
}

export function listingPath(view: AppView, serverId: number, libraryId?: number, itemId?: number) {
  const library = libraryId ?? ALL_LIBRARIES;
  const base = `/servers/${serverId}/${VIEW_SEGMENT[view]}/${library}`;
  return itemId === undefined ? base : `${base}/items/${itemId}`;
}

export const libraryPath = (serverId: number, libraryId?: number, itemId?: number) =>
  listingPath('library', serverId, libraryId, itemId);

const PATTERNS: { pattern: string; view: AppView }[] = [
  { pattern: '/servers/:serverId/libraries/:libraryId/*', view: 'library' },
  { pattern: '/servers/:serverId/trash/:libraryId/*', view: 'trash' },
  { pattern: '/servers/:serverId/collections/:libraryId/*', view: 'collections' },
];

const asId = (value?: string) => {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : undefined;
};

export function parseLocation(pathname: string): AppLocation {
  for (const { pattern, view } of PATTERNS) {
    const match = matchPath({ path: pattern, end: false }, pathname);
    if (!match) continue;

    const item = /^items\/([^/]+)$/.exec(match.params['*'] ?? '');
    return {
      serverId: asId(match.params.serverId),
      libraryId: asId(match.params.libraryId),
      view,
      itemId: asId(item?.[1]),
    };
  }
  return { view: 'library' };
}
