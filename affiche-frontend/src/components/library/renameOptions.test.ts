import { describe, expect, it } from 'vitest';

import { noSuggestionMessage, preselectedOption, renameOptions } from './renameOptions';

const suggestions = (overrides: Partial<Parameters<typeof renameOptions>[0]> = {}) => ({
  current: 'My.movie.2012.1080p',
  matched: { title: 'My Movie', provider: 'tmdb' },
  ...overrides,
});

describe('renameOptions', () => {
  it('offers the catalogue name for the id, labelled with who gave it', () => {
    expect(renameOptions(suggestions())).toEqual([
      { title: 'My Movie', source: 'TMDB · matched by id' },
    ]);
  });

  it('names whichever catalogue answered', () => {
    const [option] = renameOptions(suggestions({ matched: { title: 'X', provider: 'tvdb' } }));
    expect(option.source).toBe('TVDB · matched by id');
  });

  it('offers nothing when no id could answer', () => {

    expect(renameOptions(suggestions({ matched: null }))).toEqual([]);
  });

  it('drops a row that would change nothing', () => {
    const options = renameOptions(suggestions({
      current: 'My Movie',
      matched: { title: 'My Movie', provider: 'tmdb' },
    }));
    expect(options).toEqual([]);
  });
});

describe('preselectedOption', () => {
  it('takes the id match when there is one', () => {
    expect(preselectedOption(renameOptions(suggestions()))?.title).toBe('My Movie');
  });

  it('pre-fills nothing when no catalogue answered', () => {
    expect(preselectedOption(renameOptions(suggestions({ matched: null })))).toBeNull();
  });
});

describe('noSuggestionMessage', () => {
  it('says nothing when there is a suggestion to show', () => {
    expect(noSuggestionMessage(suggestions())).toBeNull();
  });

  it('blames the media server only when the item really has no id', () => {
    const message = noSuggestionMessage(suggestions({ matched: null, reason: 'no_id' }));
    expect(message).toMatch(/never matched it/);
  });

  it('tells an item that already agrees with the catalogue that nothing is wrong', () => {

    const message = noSuggestionMessage(suggestions({ matched: null, reason: 'already_correct' }));
    expect(message).toMatch(/already matches/);
    expect(message).not.toMatch(/never matched it/);
  });

  it('points at settings when no provider is configured', () => {
    const message = noSuggestionMessage(suggestions({ matched: null, reason: 'not_configured' }));
    expect(message).toMatch(/Settings/);
    expect(message).not.toMatch(/never matched it/);
  });

  it('says the id was not recognised rather than absent', () => {
    const message = noSuggestionMessage(suggestions({ matched: null, reason: 'not_found' }));
    expect(message).toMatch(/has an id/);
    expect(message).not.toMatch(/never matched it/);
  });

  it('falls back to a sentence rather than nothing on an unknown reason', () => {
    expect(noSuggestionMessage(suggestions({ matched: null, reason: null }))).toBeTruthy();
  });
});
