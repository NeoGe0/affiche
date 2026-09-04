export function wrapVariants(text: string, maxLines: number = 3): string[] {
  if (text.includes('\n')) return [text];

  const words = text.split(/\s+/).filter(Boolean);
  if (words.length <= 1) return [text];

  const join = (from: number, to?: number) => words.slice(from, to).join(' ');
  const variants = [text];

  for (let i = 1; i < words.length; i++) {
    variants.push(`${join(0, i)}\n${join(i)}`);
  }

  if (maxLines >= 3 && words.length >= 3) {
    for (let i = 1; i < words.length - 1; i++) {
      for (let j = i + 1; j < words.length; j++) {
        variants.push(`${join(0, i)}\n${join(i, j)}\n${join(j)}`);
      }
    }
  }

  return variants;
}
