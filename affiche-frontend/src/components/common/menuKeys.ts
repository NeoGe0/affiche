export function menuFocusIndex(key: string, current: number, enabled: readonly boolean[]): number | null {
  const count = enabled.length;
  if (count === 0 || !enabled.some(Boolean)) return null;

  const step = (from: number, direction: 1 | -1) => {
    for (let i = 1; i <= count; i++) {
      const candidate = (from + direction * i + count) % count;
      if (enabled[candidate]) return candidate;
    }
    return from;
  };

  switch (key) {
    case 'ArrowDown':
      return step(current, 1);
    case 'ArrowUp':
      return step(current < 0 ? 0 : current, -1);
    case 'Home':
      return step(-1, 1);
    case 'End':
      return step(0, -1);
    default:
      return null;
  }
}
