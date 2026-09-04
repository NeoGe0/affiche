import type { Collection } from '../../types';

const NUMBER_FORMAT = new Intl.NumberFormat();

export function memberSummary(collection: Collection): string {
  const known = collection.member_count;
  const reported = collection.child_count;
  const items = `${NUMBER_FORMAT.format(known)} item${known === 1 ? '' : 's'}`;

  if (reported == null || reported <= known) return items;
  return `${items} of ${NUMBER_FORMAT.format(reported)}`;
}
