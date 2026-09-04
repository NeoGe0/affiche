export function reconcileProviderOrder(stored: string[], added: string[]): string[] {
  const exists = new Set(added);
  const ranked = [...new Set(stored)].filter((provider) => exists.has(provider));
  const rankedSet = new Set(ranked);
  return [...ranked, ...added.filter((provider) => !rankedSet.has(provider))];
}
