import { describe, expect, it } from 'vitest';

import { fontBaseName } from './fontName';

describe('fontBaseName', () => {
  it('drops a .ttf or .otf extension', () => {
    expect(fontBaseName('BebasNeue.ttf')).toBe('BebasNeue');
    expect(fontBaseName('Inter.otf')).toBe('Inter');
  });

  it('is case-insensitive about the extension', () => {
    expect(fontBaseName('Impact.TTF')).toBe('Impact');
  });

  it('keeps dots inside the name', () => {
    expect(fontBaseName('Roboto.Condensed.ttf')).toBe('Roboto.Condensed');
    expect(fontBaseName('Archivo.Black')).toBe('Archivo.Black');
  });

  it('leaves a name with no extension alone', () => {
    expect(fontBaseName('BebasNeue')).toBe('BebasNeue');
  });
});
