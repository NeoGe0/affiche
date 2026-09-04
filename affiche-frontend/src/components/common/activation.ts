import type { KeyboardEvent } from 'react';

interface ActivationProps {
  role?: 'button';
  tabIndex?: 0;
  onClick?: () => void;
  onKeyDown?: (event: KeyboardEvent) => void;
}

export function activationProps(onActivate?: () => void): ActivationProps {
  if (!onActivate) return {};

  return {
    role: 'button',
    tabIndex: 0,
    onClick: onActivate,
    onKeyDown: (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;

      event.preventDefault();
      onActivate();
    },
  };
}
