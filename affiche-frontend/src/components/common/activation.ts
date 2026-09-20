import type { KeyboardEvent, MouseEvent } from 'react';

interface ActivationProps {
  role?: 'button';
  tabIndex?: 0;
  onClick?: (event: MouseEvent) => void;
  onKeyDown?: (event: KeyboardEvent) => void;
}

export function activationProps(onActivate?: (shiftKey: boolean) => void): ActivationProps {
  if (!onActivate) return {};

  return {
    role: 'button',
    tabIndex: 0,
    onClick: (event) => onActivate(event.shiftKey),
    onKeyDown: (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;

      event.preventDefault();
      onActivate(event.shiftKey);
    },
  };
}
