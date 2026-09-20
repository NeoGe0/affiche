import { describe, expect, it } from 'vitest';

import { currentWelcomeStep, missingTmdbWarning, stepState } from './welcomeSteps';
import type { Library } from '../../types';

const lib = (name: string, library_type: string) => ({ id: 1, media_server_id: 1, name, library_type }) as Library;

describe('currentWelcomeStep', () => {
  it('opens on the server until one is stored, however far the sources got', () => {
    expect(currentWelcomeStep(false, true)).toBe('server');
  });

  it('asks for sources after a reload with a server, since nothing stored says they were decided', () => {
    expect(currentWelcomeStep(true, false)).toBe('sources');
    expect(currentWelcomeStep(true, true)).toBe('posters');
  });

  it('marks earlier steps done and later ones upcoming', () => {
    expect(['server', 'sources', 'posters'].map((s) => stepState(s as never, 'sources')))
      .toEqual(['done', 'current', 'upcoming']);
  });
});

describe('missingTmdbWarning', () => {
  it('names the film libraries that going without TMDB leaves short', () => {
    expect(missingTmdbWarning([lib('Films', 'movie'), lib('Shows', 'show')], false))
      .toBe('Without TMDB, Films will get few posters: TVmaze only has series.');
  });

  it('says nothing when TMDB is ready or there are only series', () => {
    expect(missingTmdbWarning([lib('Films', 'movie')], true)).toBeNull();
    expect(missingTmdbWarning([lib('Shows', 'show')], false)).toBeNull();
  });
});
