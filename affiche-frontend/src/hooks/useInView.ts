import { useEffect, useState } from 'react';

export function useInView<T extends Element>(rootMargin = '200px') {
  const [element, setElement] = useState<T | null>(null);
  const [seen, setSeen] = useState(() => typeof IntersectionObserver === 'undefined');

  useEffect(() => {
    if (!element || seen) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) setSeen(true);
      },
      { rootMargin }
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [element, seen, rootMargin]);

  return [setElement, seen] as const;
}
