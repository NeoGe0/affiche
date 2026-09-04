import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { focusableElements, wrapFocusIndex } from './modalFocus';
import styles from './Modal.module.css';

interface ModalProps {

  size?: 'narrow' | 'wide' | 'large' | 'full' | 'drawer';

  label: string;

  title?: string;

  description?: React.ReactNode;

  isBusy?: boolean;

  elevated?: boolean;
  onClose: () => void;
  children: React.ReactNode;

  footer?: React.ReactNode;
}

export function Modal({
  size = 'narrow',
  label,
  title,
  description,
  isBusy = false,
  elevated = false,
  onClose,
  children,
  footer,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const close = () => { if (!isBusy) onClose(); };

  useEffect(() => {
    const opener = document.activeElement;
    panelRef.current?.focus();
    return () => {
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      close();
      return;
    }
    if (e.key !== 'Tab' || !panelRef.current) return;

    const focusable = focusableElements(panelRef.current);
    const current = focusable.indexOf(document.activeElement as HTMLElement);
    const next = wrapFocusIndex(focusable.length, current, e.shiftKey);
    if (next === -1) return;

    e.preventDefault();
    focusable[next].focus();
  };

  const handleBackdropMouseDown = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      (e.currentTarget as HTMLElement).dataset.clickStartedOnBackdrop = 'true';
    }
  };

  const handleBackdropMouseUp = (e: React.MouseEvent) => {
    if (
      e.target === e.currentTarget &&
      (e.currentTarget as HTMLElement).dataset.clickStartedOnBackdrop === 'true'
    ) {
      close();
    }
    (e.currentTarget as HTMLElement).dataset.clickStartedOnBackdrop = 'false';
  };

  const backdropVariant =
    size === 'full' ? styles.backdropTop : size === 'drawer' ? styles.backdropDrawer : '';

  return (
    <div
      className={`${styles.backdrop} ${backdropVariant} ${elevated ? styles.backdropElevated : ''}`}
      onMouseDown={handleBackdropMouseDown}
      onMouseUp={handleBackdropMouseUp}
    >
      <div
        ref={panelRef}
        className={`${styles.modal} ${size !== 'narrow' ? styles[size] : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={label}

        tabIndex={-1}
        onKeyDown={handleKeyDown}
      >
        <button
          className={styles.closeButton}
          onClick={close}
          disabled={isBusy}
          aria-label="Close"
        >
          <X size={18} />
        </button>

        {title && (
          <div className={styles.header}>
            <h2 className={styles.title}>{title}</h2>
            {description && <p className={styles.description}>{description}</p>}
          </div>
        )}

        {children}

        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </div>
  );
}
