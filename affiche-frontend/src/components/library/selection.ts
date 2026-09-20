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

export function selectRange(
  selected: ReadonlySet<number>,
  items: readonly { id: number }[],
  anchorId: number | null,
  targetId: number
): ReadonlySet<number> {
  const from = anchorId === null ? -1 : items.findIndex((item) => item.id === anchorId);
  const to = items.findIndex((item) => item.id === targetId);
  if (from === -1 || to === -1) return toggleId(selected, targetId);

  const next = new Set(selected);
  for (let i = Math.min(from, to); i <= Math.max(from, to); i++) next.add(items[i].id);
  return next;
}

export function neighbourIds(ids: readonly number[], id: number): { previous?: number; next?: number } {
  const index = ids.indexOf(id);
  if (index === -1) return {};
  return { previous: ids[index - 1], next: ids[index + 1] };
}

export function neighbours<T extends { id: number; library_id?: number }>(
  items: readonly T[],
  current: { id: number; library_id?: number }
): { previous?: T; next?: T } {
  const index = items.findIndex((item) => item.id === current.id
    && (current.library_id === undefined || item.library_id === current.library_id));
  if (index === -1) return {};
  return { previous: items[index - 1], next: items[index + 1] };
}
