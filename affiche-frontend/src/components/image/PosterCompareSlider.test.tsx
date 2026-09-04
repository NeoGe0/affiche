import { afterEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { PosterCompareSlider } from './PosterCompareSlider';
import { markCached, resetCachedImages } from '../../test/cachedImage';

const BEFORE = '/api/libraries/3/items/7/poster?v=v1&variant=source';
const AFTER = '/api/libraries/3/items/7/poster?v=v2';

const renderSlider = () =>
  render(
    <PosterCompareSlider
      beforeUrl={BEFORE}
      afterUrl={AFTER}
      alt="Severance"
      placeholder={<span>S</span>}
    />
  );

afterEach(resetCachedImages);

describe('PosterCompareSlider', () => {
  it('renders both posters, each at its own version', () => {
    renderSlider();

    const sources = screen.getAllByRole('img').map((img) => img.getAttribute('src'));
    expect(sources).toContain(BEFORE);
    expect(sources).toContain(AFTER);
  });

  it('starts centred and moves when the slider is dragged', () => {
    renderSlider();
    const slider = screen.getByRole('slider');

    expect(slider).toHaveValue('50');

    fireEvent.change(slider, { target: { value: '80' } });

    expect(slider).toHaveValue('80');
    expect(slider).toHaveAttribute('aria-valuetext', '80% original');
  });

  it('names the slider after the item, since it has no visible label', () => {
    renderSlider();

    expect(screen.getByRole('slider', { name: /original poster for Severance/i }))
      .toBeInTheDocument();
  });

  it('holds the placeholder until the generated poster has decoded', () => {
    renderSlider();

    expect(screen.getByText('S')).toBeInTheDocument();
  });

  it('drops the placeholder for a poster already in the browser cache', () => {

    markCached(AFTER);
    renderSlider();

    expect(screen.queryByText('S')).not.toBeInTheDocument();
  });
});
