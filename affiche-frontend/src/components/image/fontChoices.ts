export function fontChoices(fonts: string[], current: string): string[] {
  if (!current || fonts.includes(current)) return fonts;
  return [current, ...fonts];
}
