import type { PosterCandidate } from '../../types';

export type PosterSort = 'provider' | 'rating';

export const POSTER_SORTS: { value: PosterSort; label: string }[] = [
  { value: 'provider', label: 'Provider order' },
  { value: 'rating', label: 'Highest rated' },
];

export function sortPosterCandidates(
  posters: PosterCandidate[],
  sort: PosterSort
): PosterCandidate[] {
  if (sort === 'provider') return posters;
  return [...posters].sort((a, b) => b.rank_score - a.rank_score);
}
