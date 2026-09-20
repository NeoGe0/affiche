import type { Library } from '../../types';

export type WelcomeStep = 'server' | 'sources' | 'posters';

export const WELCOME_STEPS: WelcomeStep[] = ['server', 'sources', 'posters'];

export type StepState = 'done' | 'current' | 'upcoming';

export function currentWelcomeStep(hasServer: boolean, sourcesConfirmed: boolean): WelcomeStep {
  if (!hasServer) return 'server';
  return sourcesConfirmed ? 'posters' : 'sources';
}

export function stepState(step: WelcomeStep, current: WelcomeStep): StepState {
  const at = WELCOME_STEPS.indexOf(step);
  const now = WELCOME_STEPS.indexOf(current);
  return at < now ? 'done' : at === now ? 'current' : 'upcoming';
}

export function missingTmdbWarning(libraries: Library[], tmdbReady: boolean): string | null {
  if (tmdbReady) return null;
  const films = libraries.filter((library) => library.library_type === 'movie');
  if (films.length === 0) return null;
  const names = films.map((library) => library.name).join(', ');
  return `Without TMDB, ${names} will get few posters: TVmaze only has series.`;
}
