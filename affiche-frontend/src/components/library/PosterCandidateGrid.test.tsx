import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { PosterCandidateGrid } from './PosterCandidateGrid';
import type { PosterCandidate } from '../../types';

const CANDIDATES: PosterCandidate[] = [
  { url: 'https://image.tmdb.org/a.jpg', provider: 'tmdb', rank: 0, rank_score: 1 },
  { url: 'https://cdn.mediux.io/b.jpg', provider: 'mediux', rank: 0, rank_score: 1 },
];

function renderGrid(posters: PosterCandidate[] = CANDIDATES, onSelect = vi.fn()) {
  const { container } = render(
    <PosterCandidateGrid posters={posters} selected={null} isLoading={false} onSelect={onSelect} />
  );
  return { onSelect, container };
}

describe('PosterCandidateGrid', () => {
  it('labels each poster with the provider that supplied it', () => {
    renderGrid();

    expect(screen.getByText('TMDB')).toBeInTheDocument();
    expect(screen.getByText('MediUX')).toBeInTheDocument();
  });

  it('goes through the shared provider labels rather than showing the raw slug', () => {
    renderGrid([{ url: 'https://webservice.fanart.tv/c.jpg', provider: 'fanart', rank: 0, rank_score: 1 }]);

    expect(screen.getByText('Fanart.tv')).toBeInTheDocument();
    expect(screen.queryByText('fanart')).not.toBeInTheDocument();
  });

  it('carries the source in the accessible name, since the ribbon itself is decorative', () => {
    renderGrid();

    expect(screen.getByRole('button', { name: 'Poster 1 from TMDB' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Poster 2 from MediUX' })).toBeInTheDocument();
  });

  it('leaves the artwork itself untouched — the ribbon is a sibling, not part of the image', () => {

    const { container } = renderGrid();

    expect([...container.querySelectorAll('img')].map((img) => img.getAttribute('src')))
      .toEqual(['https://image.tmdb.org/a.jpg', 'https://cdn.mediux.io/b.jpg']);
  });

  it('selects the poster by URL alone, so the badge cannot reach what gets applied', () => {
    const { onSelect } = renderGrid();

    fireEvent.click(screen.getByRole('button', { name: 'Poster 2 from MediUX' }));

    expect(onSelect).toHaveBeenCalledWith('https://cdn.mediux.io/b.jpg');
  });

  it('renders nothing to badge when the grid is empty', () => {
    renderGrid([]);

    expect(screen.getByText('No posters found')).toBeInTheDocument();
  });
});
