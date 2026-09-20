import { useEffect, useEffectEvent, useRef, useState } from 'react';

import { libraryApi } from '../api';
import type { Library } from '../types';

interface UseLibraryUploadSettingOptions {
  library?: Library;
  enabled: boolean;
}

export function useLibraryUploadSetting({ library, enabled }: UseLibraryUploadSettingOptions) {
  const [loaded, setLoaded] = useState<{ libraryId: number; uploads: boolean } | null>(null);
  const latest = useRef(0);

  const libraryId = library?.id;
  const mediaServerId = library?.media_server_id;

  const load = useEffectEvent(async (serverId: number, id: number) => {
    const request = ++latest.current;
    try {
      const settings = await libraryApi.getLibrarySettings(serverId, id);
      if (request !== latest.current) return;
      setLoaded({ libraryId: id, uploads: !!settings.upload_enabled });
    } catch {}
  });

  useEffect(() => {
    if (!enabled || libraryId === undefined || mediaServerId === undefined) return;
    void load(mediaServerId, libraryId);
  }, [enabled, libraryId, mediaServerId]);

  return loaded && loaded.libraryId === libraryId ? loaded.uploads : undefined;
}
