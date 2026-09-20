import { useEffect, useRef, type KeyboardEvent } from 'react';

import { menuFocusIndex } from '../components/common/menuKeys';

const ITEM_SELECTOR = '[role="menuitem"]';

export function useMenuKeyboard<M extends HTMLElement, T extends HTMLElement>(
  isOpen: boolean,
  close: () => void
) {
  const menuRef = useRef<M>(null);
  const triggerRef = useRef<T>(null);

  useEffect(() => {
    if (!isOpen) return;
    const first = [...(menuRef.current?.querySelectorAll<HTMLButtonElement>(ITEM_SELECTOR) ?? [])]
      .find((item) => !item.disabled);
    first?.focus();
  }, [isOpen]);

  const onKeyDown = (event: KeyboardEvent) => {
    const items = [...(menuRef.current?.querySelectorAll<HTMLButtonElement>(ITEM_SELECTOR) ?? [])];
    if (event.key === 'Escape' || event.key === 'Tab') {
      if (event.key === 'Escape') event.preventDefault();
      close();
      triggerRef.current?.focus();
      return;
    }
    const current = items.findIndex((item) => item === document.activeElement);
    const next = menuFocusIndex(event.key, current, items.map((item) => !item.disabled));
    if (next === null) return;
    event.preventDefault();
    items[next].focus();
  };

  return { menuRef, triggerRef, onKeyDown };
}
