import { describe, it, expect } from 'vitest';

import type { LibrarySettings, OverlayOptions, PosterConfig, TextOptions } from '../../types';
import {
  customStylePatch,
  hasCustomStyle,
  INHERIT_STYLE,
  profileDeleteMessage,
  profileStylePatch,
  resolveLibraryStyle,
  stalenessMessage,
  styleModeOf,
} from './libraryStyle';
import { defaultLibrarySettings } from './mediaServerState';

const GLOBAL: PosterConfig = {
  overlay_options: { border_px: 10, border_color: '#000000' } as OverlayOptions,
  text_options: { all_caps: false, font_name: 'Inter.ttf' } as TextOptions,
  generation_options: { jpeg_quality: 90 },
};

const settings = (patch: Partial<LibrarySettings> = {}): LibrarySettings => ({
  ...defaultLibrarySettings(10),
  ...patch,
});

describe('hasCustomStyle', () => {
  it('is false when both bags are absent', () => {
    expect(hasCustomStyle(settings())).toBe(false);
    expect(hasCustomStyle(settings({ overlay_options: null, text_options: null }))).toBe(false);
  });

  it('is true when either bag is set', () => {
    expect(hasCustomStyle(settings({ overlay_options: { border_px: 4 } }))).toBe(true);
    expect(hasCustomStyle(settings({ text_options: { all_caps: true } }))).toBe(true);
  });
});

describe('resolveLibraryStyle', () => {
  it('falls back to the global style when the library has none', () => {
    const style = resolveLibraryStyle(settings(), GLOBAL);

    expect(style.overlay).toEqual(GLOBAL.overlay_options);
    expect(style.text).toEqual(GLOBAL.text_options);
  });

  it('layers a stored bag over the global one, so keys it predates still have a value', () => {
    const style = resolveLibraryStyle(settings({ overlay_options: { border_px: 42 } }), GLOBAL);

    expect(style.overlay.border_px).toBe(42);
    expect(style.overlay.border_color).toBe('#000000');
  });

  it('resolves each bag independently', () => {
    const style = resolveLibraryStyle(settings({ text_options: { all_caps: true } }), GLOBAL);

    expect(style.text.all_caps).toBe(true);
    expect(style.overlay).toEqual(GLOBAL.overlay_options);
  });
});

describe('styleModeOf', () => {
  it('is global with no profile and no inline columns', () => {
    expect(styleModeOf(settings())).toBe('global');
  });

  it('is custom when the inline columns are set', () => {
    expect(styleModeOf(settings({ overlay_options: { border_px: 7 } }))).toBe('custom');
  });

  it('is profile whenever one is assigned, even alongside inline columns', () => {

    expect(styleModeOf(settings({ style_profile_id: 3, overlay_options: { border_px: 7 } })))
      .toBe('profile');
  });
});

describe('resolveLibraryStyle with a profile', () => {
  const profile = {
    id: 3,
    name: 'Kids',
    overlay_options: { border_px: 99 },
    text_options: null,
    library_count: 1,
  };

  it('takes the profile over the library\'s own columns rather than merging them', () => {
    const style = resolveLibraryStyle(
      settings({ style_profile_id: 3, overlay_options: { border_px: 7 } }),
      GLOBAL,
      [profile]
    );

    expect(style.overlay.border_px).toBe(99);
  });

  it('falls back to the global style for a half the profile does not override', () => {
    const style = resolveLibraryStyle(settings({ style_profile_id: 3 }), GLOBAL, [profile]);

    expect(style.text).toEqual(GLOBAL.text_options);
  });

  it('falls back to the library\'s own columns when the profile is missing', () => {
    const style = resolveLibraryStyle(
      settings({ style_profile_id: 404, overlay_options: { border_px: 7 } }),
      GLOBAL,
      [profile]
    );

    expect(style.overlay.border_px).toBe(7);
  });
});

describe('profileStylePatch', () => {
  it('clears the inline columns the profile would shadow anyway', () => {
    expect(profileStylePatch(3)).toEqual({
      overlay_options: null,
      text_options: null,
      style_profile_id: 3,
    });
  });
});

describe('profileDeleteMessage', () => {
  const profile = (library_count: number) => ({
    id: 3,
    name: 'Kids',
    library_count,
  });

  it('says plainly when nothing uses it', () => {
    expect(profileDeleteMessage(profile(0))).toBe('Delete "Kids"? No library is using it.');
  });

  it('names the consequence for the libraries that do', () => {
    expect(profileDeleteMessage(profile(3))).toContain(
      '3 libraries using it will fall back to the global style'
    );
  });

  it('agrees in number for a single library', () => {
    expect(profileDeleteMessage(profile(1))).toContain('1 library using it will fall back');
  });
});

describe('stalenessMessage', () => {
  it('says nothing when there is nothing stale', () => {
    expect(stalenessMessage(null)).toBeNull();
    expect(stalenessMessage({ stale: 0, total: 340 })).toBeNull();
  });

  it('reports the count against the total', () => {
    expect(stalenessMessage({ stale: 12, total: 340 })).toBe(
      '12 of 340 posters were generated with an earlier style.'
    );
  });

  it('says "poster" for a single one', () => {
    expect(stalenessMessage({ stale: 1, total: 340 })).toBe(
      '1 of 340 poster was generated with an earlier style.'
    );
  });
});

describe('style patches', () => {
  it('INHERIT_STYLE nulls both columns and detaches any profile', () => {
    expect(INHERIT_STYLE).toEqual({
      overlay_options: null,
      text_options: null,
      style_profile_id: null,
    });
  });

  it('customStylePatch detaches the profile, since an inline style replaces it', () => {
    const patch = customStylePatch(resolveLibraryStyle(settings(), GLOBAL));

    expect(patch.style_profile_id).toBeNull();
  });

  it('customStylePatch copies the style rather than aliasing it', () => {
    const style = resolveLibraryStyle(settings(), GLOBAL);

    const patch = customStylePatch(style);

    expect(patch.overlay_options).toEqual(GLOBAL.overlay_options);
    expect(patch.overlay_options).not.toBe(style.overlay);
  });
});
