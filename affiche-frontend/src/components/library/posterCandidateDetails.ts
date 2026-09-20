import type { PosterCandidate } from '../../types';

export const SMALL_POSTER_WIDTH = 1000;

export interface CandidateDetails {

  language: string | null;

  size: string | null;
  isSmall: boolean;
}

export function candidateDetails({ language, textless, width, height }: PosterCandidate): CandidateDetails {
  return {
    language: textless ? 'Textless' : language ? language.toUpperCase() : null,
    size: width && height ? `${width}×${height}` : null,
    isSmall: !!width && width < SMALL_POSTER_WIDTH,
  };
}

export function candidateDetailsLabel(details: CandidateDetails): string {
  return [
    details.language,
    details.size && `${details.size.replace('×', ' by ')}${details.isSmall ? ', small' : ''}`,
  ]
    .filter(Boolean)
    .join(', ');
}
