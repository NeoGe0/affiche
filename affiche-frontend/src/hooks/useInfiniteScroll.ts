import { useEffect, useState } from 'react';

const PREFETCH_MARGIN = '100px';

interface UseInfiniteScrollOptions {

  hasMore: boolean;

  isLoadingMore: boolean;

  onLoadMore?: () => void;
}

export function useInfiniteScroll({
  hasMore,
  isLoadingMore,
  onLoadMore,
}: UseInfiniteScrollOptions) {
  const [sentinel, setSentinel] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!sentinel || !hasMore || isLoadingMore || !onLoadMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) onLoadMore();
      },
      { root: null, rootMargin: PREFETCH_MARGIN, threshold: 0 }
    );
    observer.observe(sentinel);

    return () => observer.disconnect();
  }, [sentinel, hasMore, isLoadingMore, onLoadMore]);

  return setSentinel;
}
