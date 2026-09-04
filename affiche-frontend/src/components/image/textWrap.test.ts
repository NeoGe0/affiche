import { describe, expect, it } from 'vitest';

import { wrapVariants } from './textWrap';

describe('wrapVariants', () => {
  it('offers the unwrapped text first, so a wrap that buys nothing loses the tie', () => {
    expect(wrapVariants('Blade Runner')[0]).toBe('Blade Runner');
  });

  it('enumerates every two-line split', () => {
    expect(wrapVariants('A B C', 2)).toEqual(['A B C', 'A\nB C', 'A B\nC']);
  });

  it('adds every three-line split after the two-line ones', () => {
    expect(wrapVariants('A B C')).toEqual([
      'A B C',
      'A\nB C',
      'A B\nC',
      'A\nB\nC',
    ]);
  });

  it('leaves text that already contains a break alone', () => {
    expect(wrapVariants('Alien\nResurrection')).toEqual(['Alien\nResurrection']);
  });

  it('has nothing to split for a single word', () => {
    expect(wrapVariants('Dune')).toEqual(['Dune']);
    expect(wrapVariants('')).toEqual(['']);
  });

  it('splits on runs of whitespace and drops the empties, like Python str.split()', () => {
    expect(wrapVariants('  Blade   Runner ', 2)).toEqual([
      '  Blade   Runner ',
      'Blade\nRunner',
    ]);
  });

  it('matches the backend enumeration for four words', () => {
    expect(wrapVariants('A B C D')).toEqual([
      'A B C D',
      'A\nB C D',
      'A B\nC D',
      'A B C\nD',
      'A\nB\nC D',
      'A\nB C\nD',
      'A B\nC\nD',
    ]);
  });
});
