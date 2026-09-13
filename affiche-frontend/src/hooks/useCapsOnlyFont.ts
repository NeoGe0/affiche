import { useEffect, useState } from 'react';

import { isCapsOnlyFont } from '../components/image/capsOnlyFont';

interface Measurement {
  font: string;
  capsOnly: boolean;
}

export function useCapsOnlyFont(fontFile: string | undefined, available: string[]): boolean {
  const [measured, setMeasured] = useState<Measurement | null>(null);

  useEffect(() => {
    if (!fontFile) return;

    let current = true;
    isCapsOnlyFont(fontFile).then((capsOnly) => {
      if (current) setMeasured({ font: fontFile, capsOnly });
    });

    return () => {
      current = false;
    };
  }, [fontFile, available]);

  return measured !== null && measured.font === fontFile && measured.capsOnly;
}
