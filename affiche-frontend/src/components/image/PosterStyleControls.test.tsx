import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { fireEvent } from '@testing-library/dom';

import type { OverlayOptions, TextOptions } from '../../types';
import { PosterStyleControls } from './PosterStyleControls';

const capsOnly = vi.hoisted(() => ({ value: false }));
vi.mock('../../hooks/useCapsOnlyFont', () => ({
  useCapsOnlyFont: () => capsOnly.value,
}));

const TEXT: TextOptions = {
  enabled: true,
  font_name: 'Inter.ttf',
  font_color: '#FFFFFF',
  all_caps: true,
  min_font_ratio: 0.015,
  max_font_ratio: 0.1,
  max_width_ratio: 0.95,
  max_height_ratio: 0.167,
  text_offset_ratio: 0.143,
  border_padding_ratio: 0,
  gravity: 'south',
  stroke_enabled: false,
  stroke_color: '#000000',
  stroke_width_ratio: 0.02,
  line_spacing_ratio: 0,
  break_on_symbols: true,
  break_symbols: [' - '],
  auto_wrap: true,
  auto_wrap_threshold_ratio: 0.067,
};

function renderControls(text: Partial<TextOptions> = {}) {
  const onTextChange = vi.fn();
  render(
    <PosterStyleControls
      overlayOptions={{ border_enabled: true } as OverlayOptions}
      textOptions={{ ...TEXT, ...text }}
      onOverlayChange={vi.fn()}
      onTextChange={onTextChange}
      fonts={['Inter.ttf']}
    />
  );
  return onTextChange;
}

function renderOverlayControls(overlay: Partial<OverlayOptions> = {}) {
  const onOverlayChange = vi.fn();
  render(
    <PosterStyleControls
      overlayOptions={{ border_enabled: true, ...overlay } as OverlayOptions}
      textOptions={TEXT}
      onOverlayChange={onOverlayChange}
      onTextChange={vi.fn()}
      fonts={['Inter.ttf']}
    />
  );
  return onOverlayChange;
}

describe('PosterStyleControls gradient', () => {
  it('sends the solid band as a ratio of the poster height', () => {

    const onOverlayChange = renderOverlayControls();

    fireEvent.change(screen.getByLabelText('Solid height'), { target: { value: '35' } });

    expect(onOverlayChange).toHaveBeenCalledWith({ matte_height_ratio: 0.35 });
  });

  it('allows no solid band at all', () => {
    const onOverlayChange = renderOverlayControls({ matte_height_ratio: 0.35 });

    fireEvent.change(screen.getByLabelText('Solid height'), { target: { value: '0' } });

    expect(onOverlayChange).toHaveBeenCalledWith({ matte_height_ratio: 0 });
  });
});

describe('PosterStyleControls gradient direction', () => {
  it('sends the edge the matte grows from', () => {
    const onOverlayChange = renderOverlayControls({ gradient_direction: 'bottom' });

    fireEvent.change(screen.getByLabelText('Direction'), { target: { value: 'left' } });

    expect(onOverlayChange).toHaveBeenCalledWith({ gradient_direction: 'left' });
  });
});

describe('PosterStyleControls line layout', () => {
  it('sends line spacing as a ratio of the font size', () => {
    const onTextChange = renderControls();

    fireEvent.change(screen.getByLabelText('Line spacing'), { target: { value: '40' } });

    expect(onTextChange).toHaveBeenCalledWith({ line_spacing_ratio: 0.4 });
  });

  it('allows negative line spacing, which pulls stacked lines together', () => {
    const onTextChange = renderControls();

    fireEvent.change(screen.getByLabelText('Line spacing'), { target: { value: '-15' } });

    expect(onTextChange).toHaveBeenCalledWith({ line_spacing_ratio: -0.15 });
  });

  it('sends the text block height, which is what line spacing competes against', () => {
    const onTextChange = renderControls();

    fireEvent.change(screen.getByLabelText('Text block height'), { target: { value: '45' } });

    expect(onTextChange).toHaveBeenCalledWith({ max_height_ratio: 0.45 });
  });

  it('re-bases the offset when the title moves to the centre', () => {

    const onTextChange = renderControls({ gravity: 'south', text_offset_ratio: 0.143 });

    fireEvent.change(screen.getByLabelText('Position'), { target: { value: 'center' } });

    expect(onTextChange).toHaveBeenCalledWith({ gravity: 'center', text_offset_ratio: 0.5 });
  });

  it('leaves a chosen centre offset alone when the position is already centre', () => {
    const onTextChange = renderControls({ gravity: 'center', text_offset_ratio: 0.7 });

    fireEvent.change(screen.getByLabelText('Vertical position'), { target: { value: '30' } });

    expect(onTextChange).toHaveBeenCalledWith({ text_offset_ratio: 0.3 });
  });

  it('sends text width as a ratio of the poster width', () => {
    const onTextChange = renderControls();

    fireEvent.change(screen.getByLabelText('Text width'), { target: { value: '60' } });

    expect(onTextChange).toHaveBeenCalledWith({ max_width_ratio: 0.6 });
  });

  it('turns automatic line breaks off', () => {
    const onTextChange = renderControls();

    fireEvent.click(screen.getByLabelText('Auto line breaks'));

    expect(onTextChange).toHaveBeenCalledWith({ auto_wrap: false });
  });

  it('reflects the options it was given rather than its own state', () => {
    renderControls({ auto_wrap: false, line_spacing_ratio: 0.25 });

    expect(screen.getByLabelText('Auto line breaks')).not.toBeChecked();
    expect(screen.getByLabelText('Line spacing')).toHaveValue('25');
  });
});

describe('PosterStyleControls on a caps-only font', () => {
  afterEach(() => {
    capsOnly.value = false;
  });

  it('leaves All caps usable on a font that has lowercase', () => {
    renderControls();

    expect(screen.getByLabelText('All caps')).toBeEnabled();
    expect(screen.queryByText(/has no lowercase/)).not.toBeInTheDocument();
  });

  it('disables All caps and says why when the font has no lowercase', () => {
    capsOnly.value = true;

    renderControls({ font_name: 'BebasNeue-Regular.ttf' });

    expect(screen.getByLabelText('All caps')).toBeDisabled();
    expect(screen.getByText(/BebasNeue-Regular has no lowercase/)).toBeInTheDocument();
  });
});

describe('PosterStyleControls effects', () => {
  it('patches vignette, glow and grain as the 0–1 ratios the renderers read', () => {
    const onOverlayChange = renderOverlayControls({
      vignette_strength: 0, vignette_color: '#000000',
      inner_glow_strength: 0, inner_glow_color: '#ffffff',
      grain_amount: 0, grain_size: 1,
    });

    fireEvent.change(screen.getByLabelText('Vignette'), { target: { value: '40' } });
    fireEvent.change(screen.getByLabelText('Inner glow'), { target: { value: '25' } });
    fireEvent.change(screen.getByLabelText('Grain'), { target: { value: '10' } });

    expect(onOverlayChange).toHaveBeenCalledWith({ vignette_strength: 0.4 });
    expect(onOverlayChange).toHaveBeenCalledWith({ inner_glow_strength: 0.25 });
    expect(onOverlayChange).toHaveBeenCalledWith({ grain_amount: 0.1 });
  });

  it('holds a colour or size back until its effect is on, since it would change nothing', () => {
    renderOverlayControls({
      vignette_strength: 0, vignette_color: '#000000',
      inner_glow_strength: 0.3, inner_glow_color: '#ffffff',
      grain_amount: 0, grain_size: 1,
    });

    expect(screen.getByLabelText('Vignette color')).toBeDisabled();
    expect(screen.getByLabelText('Glow color')).toBeEnabled();
    expect(screen.getByLabelText('Grain size')).toBeDisabled();
  });
});
