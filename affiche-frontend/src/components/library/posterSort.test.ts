import { describe, expect, it } from 'vitest';

import { sortPosterCandidates } from './posterSort';
import type { PosterCandidate } from '../../types';

const candidate = (
  provider: string,
  rank: number,
  rank_score: number
): PosterCandidate => ({ url: `https://cdn/${provider}-${rank}.jpg`, provider, rank, rank_score });

const GRID: PosterCandidate[] = [
  candidate('tmdb', 0, 1),
  candidate('tmdb', 1, 0.5),
  candidate('tmdb', 2, 0),
  candidate('mediux', 0, 1),
  candidate('mediux', 1, 0),
];

describe('sortPosterCandidates', () => {
  it('leaves provider order exactly as the backend sent it', () => {
    expect(sortPosterCandidates(GRID, 'provider')).toBe(GRID);
  });

  it('interleaves the providers by rank when sorting on rating', () => {
    const sorted = sortPosterCandidates(GRID, 'rating');

    expect(sorted.map((p) => [p.provider, p.rank])).toEqual([
      ['tmdb', 0],
      ['mediux', 0],
      ['tmdb', 1],
      ['tmdb', 2],
      ['mediux', 1],
    ]);
  });

  it('keeps ties in provider order, so the top of the grid follows the configured order', () => {
    const sorted = sortPosterCandidates(GRID, 'rating');

    expect(sorted.slice(0, 2).map((p) => p.provider)).toEqual(['tmdb', 'mediux']);
  });

  it('does not mutate the array it was given', () => {
    const original = [...GRID];
    sortPosterCandidates(GRID, 'rating');

    expect(GRID).toEqual(original);
  });

  it('handles an empty grid', () => {
    expect(sortPosterCandidates([], 'rating')).toEqual([]);
  });

  it('ranks a provider that returned one poster alongside the other providers best', () => {

    const lone = candidate('shoko', 0, 1);
    const sorted = sortPosterCandidates([...GRID, lone], 'rating');

    expect(sorted.slice(0, 3).map((p) => p.provider)).toEqual(['tmdb', 'mediux', 'shoko']);
  });
});
