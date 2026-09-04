export interface LanguageOption {
  value: string;
  label: string;
}

export const TEXTLESS = '';

export const TEXTLESS_LABEL = 'Textless';

export const POSTER_LANGUAGES: LanguageOption[] = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'es', label: 'Spanish' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'nl', label: 'Dutch' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'zh', label: 'Chinese' },
];

export const ORDERABLE_LANGUAGES: LanguageOption[] = [
  { value: TEXTLESS, label: TEXTLESS_LABEL },
  ...POSTER_LANGUAGES,
];

export function languageLabel(value: string): string {
  return ORDERABLE_LANGUAGES.find((lang) => lang.value === value)?.label ?? value;
}
