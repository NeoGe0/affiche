import { useState, type ReactNode } from 'react';
import { MoreVertical } from 'lucide-react';

import { usePopoverDismiss } from '../../hooks/usePopoverDismiss';
import { useMenuKeyboard } from '../../hooks/useMenuKeyboard';

import styles from './OverflowMenu.module.css';

export interface OverflowMenuItem {

  icon?: ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;

  danger?: boolean;
}

interface OverflowMenuProps {
  items: OverflowMenuItem[];

  title?: string;

  triggerClassName?: string;

  placement?: 'bottom-end' | 'top-start';
}

export function OverflowMenu({
  items, title = 'More actions', triggerClassName, placement = 'bottom-end',
}: OverflowMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = usePopoverDismiss<HTMLDivElement>(isOpen, () => setIsOpen(false));
  const { menuRef: dropdownRef, triggerRef, onKeyDown } =
    useMenuKeyboard<HTMLDivElement, HTMLButtonElement>(isOpen, () => setIsOpen(false));

  if (items.length === 0) return null;

  return (
    <div className={styles.menu} ref={menuRef}>
      <button
        ref={triggerRef}
        className={`${styles.trigger} ${triggerClassName ?? styles.triggerSkin} ${isOpen ? styles.triggerActive : ''}`}
        onClick={() => setIsOpen((open) => !open)}
        title={title}
        aria-haspopup="menu"
        aria-expanded={isOpen}
      >
        <MoreVertical size={16} />
      </button>

      {isOpen && (
        <div
          ref={dropdownRef}
          className={`${styles.dropdown} ${placement === 'top-start' ? styles.dropdownTopStart : ''}`}
          role="menu"
          onKeyDown={onKeyDown}
        >
          {items.map((item, index) => (
            <div key={item.label}>
              {item.danger && index > 0 && <div className={styles.divider} />}
              <button
                className={`${styles.item} ${item.danger ? styles.itemDanger : ''}`}
                role="menuitem"
                tabIndex={-1}
                disabled={item.disabled}
                onClick={() => {
                  setIsOpen(false);
                  item.onClick();
                }}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
