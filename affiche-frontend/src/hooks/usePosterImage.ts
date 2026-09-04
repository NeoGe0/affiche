import { useCallback, useState } from 'react';

export function usePosterImage(imageUrl: string) {
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);

  const imgRef = useCallback(
    (img: HTMLImageElement | null) => {
      if (img && img.complete && img.naturalWidth > 0) setLoadedUrl(imageUrl);
    },
    [imageUrl]
  );

  return {
    isLoaded: loadedUrl === imageUrl,
    isError: failedUrl === imageUrl,
    imgKey: imageUrl,
    imgRef,
    onLoad: () => setLoadedUrl(imageUrl),
    onError: () => setFailedUrl(imageUrl),
  };
}
