import { arrayMove } from '@dnd-kit/sortable';

export function moveItem<T>(order: T[], from: number, to: number): T[] {
  if (from === to) return order;
  if (from < 0 || from >= order.length) return order;
  if (to < 0 || to >= order.length) return order;
  return arrayMove(order, from, to);
}
