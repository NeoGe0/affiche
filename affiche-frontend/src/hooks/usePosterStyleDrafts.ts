import { useState } from 'react';

import type { OverlayOptions, PosterConfig, TextOptions } from '../types';

const FALLBACK_QUALITY = 90;

export function usePosterStyleDrafts(posterConfig: PosterConfig | null) {
  const [overlayDraft, setOverlayDraft] = useState<OverlayOptions | null>(null);
  const [textDraft, setTextDraft] = useState<TextOptions | null>(null);
  const [qualityDraft, setQualityDraft] = useState<number | null>(null);

  const overlayOptions = overlayDraft ?? posterConfig?.overlay_options;
  const textOptions = textDraft ?? posterConfig?.text_options;
  const quality = qualityDraft ?? posterConfig?.generation_options.jpeg_quality ?? FALLBACK_QUALITY;

  return {

    overlayOptions,
    textOptions,
    quality,

    changeOverlay: (changes: Partial<OverlayOptions>) => {
      if (overlayOptions) setOverlayDraft({ ...overlayOptions, ...changes });
    },
    changeText: (changes: Partial<TextOptions>) => {
      if (textOptions) setTextDraft({ ...textOptions, ...changes });
    },
    changeQuality: setQualityDraft,

    reset: () => {
      setOverlayDraft(null);
      setTextDraft(null);
      setQualityDraft(null);
    },
  };
}
