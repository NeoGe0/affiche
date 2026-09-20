import { describe, expect, it } from 'vitest';

import { candidateDetails, candidateDetailsLabel } from './posterCandidateDetails';

const base = { url: 'u', provider: 'tmdb', rank: 0, rank_score: 1 };

describe('candidateDetails', () => {
  it('says Textless only when the provider marked it so', () => {
    expect(candidateDetails({ ...base, textless: true }).language).toBe('Textless');
    expect(candidateDetails({ ...base, textless: null }).language).toBeNull();
    expect(candidateDetails({ ...base, language: 'fr', textless: false }).language).toBe('FR');
  });

  it('shows a size only when both sides are known, and flags a small one', () => {
    expect(candidateDetails({ ...base, width: 2000, height: 3000 })).toMatchObject({
      size: '2000×3000',
      isSmall: false,
    });
    expect(candidateDetails({ ...base, width: 680, height: 1000 }).isSmall).toBe(true);
    expect(candidateDetails({ ...base, width: 680 }).size).toBeNull();
  });

  it('says nothing for a provider that published nothing', () => {
    const details = candidateDetails(base);

    expect(details).toEqual({ language: null, size: null, isSmall: false });
    expect(candidateDetailsLabel(details)).toBe('');
  });

  it('puts the same details into words for the accessible name', () => {
    expect(candidateDetailsLabel(candidateDetails({ ...base, textless: true, width: 680, height: 1000 })))
      .toBe('Textless, 680 by 1000, small');
  });
});
