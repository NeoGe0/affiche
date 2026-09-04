const EMPTY: ReadonlySet<number> = new Set();

export const emptySelection = () => EMPTY;

export function toggleId(selected: ReadonlySet<number>, id: number): ReadonlySet<number> {
  const next = new Set(selected);
  if (!next.delete(id)) next.add(id);
  return next;
}

export function toggleAll(
  selected: ReadonlySet<number>,
  items: readonly { id: number }[]
): ReadonlySet<number> {
  if (items.length > 0 && items.every((item) => selected.has(item.id))) return EMPTY;
  return new Set(items.map((item) => item.id));
}

export function pruneSelection(
  selected: ReadonlySet<number>,
  items: readonly { id: number }[]
): ReadonlySet<number> {
  if (selected.size === 0) return selected;

  const listed = new Set(items.map((item) => item.id));
  const kept = [...selected].filter((id) => listed.has(id));
  return kept.length === selected.size ? selected : new Set(kept);
}
