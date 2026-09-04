import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

describe('test harness', () => {
  it('renders a component and matches on the DOM', () => {
    render(<p>harness ok</p>);
    expect(screen.getByText('harness ok')).toBeInTheDocument();
  });

  it('jsdom does not load images: complete/naturalWidth stay falsy', () => {
    const img = document.createElement('img');
    img.src = '/poster.png';

    expect(img.complete).toBe(false);
    expect(img.naturalWidth).toBe(0);
  });

  it('img.complete can be stubbed per-element for cached-image tests', () => {
    const img = document.createElement('img');
    Object.defineProperty(img, 'complete', { value: true, configurable: true });
    Object.defineProperty(img, 'naturalWidth', { value: 500, configurable: true });

    expect(img.complete).toBe(true);
    expect(img.naturalWidth).toBe(500);
  });
});
