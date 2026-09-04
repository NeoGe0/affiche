import { describe, expect, it } from 'vitest';

import { bucketLetter } from './alphaBucket';

describe('bucketLetter', () => {

  it('agrees with the backend on its pinned cases', () => {
    expect(bucketLetter('The Matrix')).toBe('T');
    expect(bucketLetter('avatar')).toBe('A');
    expect(bucketLetter('300')).toBe('#');
  });

  it('uppercases the first letter', () => {
    expect(bucketLetter('zodiac')).toBe('Z');
    expect(bucketLetter('Zodiac')).toBe('Z');
  });

  it('does not strip leading articles', () => {
    expect(bucketLetter('The Thing')).toBe('T');
    expect(bucketLetter('A Serious Man')).toBe('A');
  });

  it('ignores surrounding whitespace', () => {
    expect(bucketLetter('  Fargo')).toBe('F');
    expect(bucketLetter('\tHeat ')).toBe('H');
  });

  it('buckets anything that is not A-Z under #', () => {
    expect(bucketLetter('')).toBe('#');
    expect(bucketLetter('   ')).toBe('#');
    expect(bucketLetter('1917')).toBe('#');
    expect(bucketLetter('¡Three Amigos!')).toBe('#');
    expect(bucketLetter('日本語')).toBe('#');
  });

  it('buckets an accented initial under #, as the backend does', () => {
    expect(bucketLetter('Élite')).toBe('#');
    expect(bucketLetter('Ámbar')).toBe('#');
  });
});
