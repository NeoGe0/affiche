import { Film, Library, Tv } from 'lucide-react';

import { MEDIA_SERVER_BRAND } from '../../constants/mediaServers';
import type { MediaServerType } from '../../types';

interface MediaServerIconProps {
  type: MediaServerType;
  size?: number;

  color?: string;
}

export function MediaServerIcon({ type, size = 16, color }: MediaServerIconProps) {
  const brand = MEDIA_SERVER_BRAND[type];

  if (!brand) return <Library size={size} />;

  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={color ?? brand.color} aria-hidden="true">
      <path d={brand.path} />
    </svg>
  );
}

interface LibraryTypeIconProps {

  type: string;
  size?: number;
}

export function LibraryTypeIcon({ type, size = 16 }: LibraryTypeIconProps) {
  if (type === 'movie') return <Film size={size} />;
  if (type === 'show') return <Tv size={size} />;
  return <Library size={size} />;
}
