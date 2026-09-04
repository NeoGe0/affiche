import type {
  LibrarySettings,
  LibraryStyleStaleness,
  OverlayOptions,
  PosterConfig,
  StyleProfile,
  TextOptions,
} from '../../types';

export interface LibraryStyle {
  overlay: OverlayOptions;
  text: TextOptions;
}

export type StyleMode = 'global' | 'profile' | 'custom';

export function styleModeOf(settings: LibrarySettings): StyleMode {
  if (settings.style_profile_id != null) return 'profile';
  if (settings.overlay_options || settings.text_options) return 'custom';
  return 'global';
}

export function hasCustomStyle(settings: LibrarySettings): boolean {
  return styleModeOf(settings) !== 'global';
}

export function resolveLibraryStyle(
  settings: LibrarySettings,
  config: PosterConfig,
  profiles: StyleProfile[] = []
): LibraryStyle {
  const profile =
    settings.style_profile_id != null
      ? profiles.find((candidate) => candidate.id === settings.style_profile_id)
      : undefined;

  const source = profile ?? settings;
  return {
    overlay: { ...config.overlay_options, ...(source.overlay_options as Partial<OverlayOptions>) },
    text: { ...config.text_options, ...(source.text_options as Partial<TextOptions>) },
  };
}

export function profileDeleteMessage(profile: StyleProfile): string {
  if (profile.library_count === 0) {
    return `Delete "${profile.name}"? No library is using it.`;
  }
  const libraries =
    profile.library_count === 1 ? '1 library' : `${profile.library_count} libraries`;
  return `Delete "${profile.name}"? ${libraries} using it will fall back to the global style. Their existing posters are left alone.`;
}

export function profileEditWarning(profile: StyleProfile): string | null {
  if (profile.library_count === 0) return null;
  const libraries =
    profile.library_count === 1 ? '1 library uses' : `${profile.library_count} libraries use`;
  return `${libraries} this profile. Saving restyles them all, but only from their next generation — existing posters keep the style they were made with.`;
}

export function profileStylePatch(
  profileId: number
): Pick<LibrarySettings, 'overlay_options' | 'text_options' | 'style_profile_id'> {
  return { overlay_options: null, text_options: null, style_profile_id: profileId };
}

export function stalenessMessage(staleness: LibraryStyleStaleness | null): string | null {
  if (!staleness || staleness.stale === 0) return null;
  const subject = staleness.stale === 1 ? 'poster was' : 'posters were';
  return `${staleness.stale} of ${staleness.total} ${subject} generated with an earlier style.`;
}

type StylePatch = Pick<LibrarySettings, 'overlay_options' | 'text_options' | 'style_profile_id'>;

export const INHERIT_STYLE: StylePatch = {
  overlay_options: null,
  text_options: null,
  style_profile_id: null,
};

export function customStylePatch(style: LibraryStyle): StylePatch {
  return {
    overlay_options: { ...style.overlay },
    text_options: { ...style.text },
    style_profile_id: null,
  };
}
