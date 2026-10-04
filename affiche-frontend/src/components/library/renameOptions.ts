import type { ItemTitleSuggestions, NoSuggestionReason } from '../../types';

export interface RenameOption {

  title: string;

  source: string;
}

export function renameOptions(suggestions: ItemTitleSuggestions): RenameOption[] {
  const { matched } = suggestions;
  if (!matched || matched.title === suggestions.current.trim()) return [];

  return [{
    title: matched.title,
    source: `${matched.provider.toUpperCase()} · matched by id`,
  }];
}

export function preselectedOption(options: RenameOption[]): RenameOption | null {
  return options[0] ?? null;
}

export function noSuggestionMessage(
  suggestions: ItemTitleSuggestions
): string | null {
  if (suggestions.matched) return null;

  const messages: Record<NoSuggestionReason, string> = {
    no_id: 'No TMDB or TVDB id on this item, so there is nothing to look it up by — your media '
      + 'server never matched it. Type the title you want below.',
    not_configured: 'No poster provider is configured, so no catalogue can be asked. Add one in '
      + 'Settings, or type the title you want below.',
    not_found: 'This item has an id, but no configured catalogue recognised it. Type the title you '
      + 'want below.',
    already_correct: 'This title already matches what the catalogue calls it — there is nothing to '
      + 'correct. You can still change it below.',
  };
  return messages[suggestions.reason ?? 'no_id'] ?? messages.no_id;
}
