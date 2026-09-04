import { Film, Tv, Image, Layers, MonitorPlay, Server } from 'lucide-react';
import type { ReactNode } from 'react';
import type { PosterProvider } from '../../constants/providers';

export const PROVIDER_ICONS: Record<PosterProvider, ReactNode> = {
  tmdb: <Film size={18} />,
  tvdb: <Tv size={18} />,
  fanart: <Image size={18} />,
  mediux: <Layers size={18} />,
  tvmaze: <MonitorPlay size={18} />,
  shoko: <Server size={18} />,
};
