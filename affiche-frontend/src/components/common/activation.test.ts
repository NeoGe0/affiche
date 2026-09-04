import { describe, expect, it, vi } from 'vitest';
import type { KeyboardEvent } from 'react';

import { activationProps } from './activation';

const keyEvent = (key: string) =>
  ({ key, preventDefault: vi.fn() }) as unknown as KeyboardEvent & { preventDefault: () => void };

describe('activationProps', () => {
  it('marks the element as an activatable button', () => {
    const props = activationProps(() => {});

    expect(props.role).toBe('button');
    expect(props.tabIndex).toBe(0);
  });

  it.each(['Enter', ' '])('activates on %j', (key) => {
    const onActivate = vi.fn();
    const event = keyEvent(key);

    activationProps(onActivate).onKeyDown?.(event);

    expect(onActivate).toHaveBeenCalledOnce();

    expect(event.preventDefault).toHaveBeenCalled();
  });

  it.each(['Tab', 'a', 'ArrowDown', 'Escape'])('ignores %j', (key) => {
    const onActivate = vi.fn();
    const event = keyEvent(key);

    activationProps(onActivate).onKeyDown?.(event);

    expect(onActivate).not.toHaveBeenCalled();
    expect(event.preventDefault).not.toHaveBeenCalled();
  });

  it('yields no props without a callback, rather than a focusable no-op', () => {
    expect(activationProps(undefined)).toEqual({});
  });
});
