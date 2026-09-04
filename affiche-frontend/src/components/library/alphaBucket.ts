export function bucketLetter(title: string): string {
  const ch = (title || '').trim().charAt(0).toUpperCase();
  return ch >= 'A' && ch <= 'Z' ? ch : '#';
}
