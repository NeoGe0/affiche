import { useEffect, useEffectEvent, useRef } from 'react';

export function usePopoverDismiss<T extends HTMLElement>(isOpen: boolean, onDismiss: () => void) {
  const ref = useRef<T>(null);

  const dismiss = useEffectEvent(() => onDismiss());

  useEffect(() => {
    if (!isOpen) return;
    const handlePointer = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) dismiss();
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismiss();
    };
    document.addEventListener('mousedown', handlePointer);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handlePointer);
      document.removeEventListener('keydown', handleKey);
    };
  }, [isOpen]);

  return ref;
}
