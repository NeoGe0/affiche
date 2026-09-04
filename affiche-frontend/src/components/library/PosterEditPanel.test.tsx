import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { fireEvent } from '@testing-library/dom';

import type { OverlayOptions, TextOptions } from '../../types';
import { PosterEditPanel } from './PosterEditPanel';

vi.mock('../image/PosterRenderer', () => ({ drawPoster: vi.fn(() => new Promise(() => {})) }));
vi.mock('../../hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../hooks')>()),
  useFonts: () => ({ fonts: ['Inter.ttf'], isLoading: false }),
}));

function renderPanel(title: string) {
  const onTitleChange = vi.fn();
  render(
    <PosterEditPanel
      imageUrl="/a.jpg"
      title={title}
      onTitleChange={onTitleChange}
      titleLanguage=""
      onTitleLanguageChange={vi.fn()}
      titleLanguageEnabled
      isTranslating={false}
      titleNotFound={false}
      overlayOptions={{ border_enabled: false } as OverlayOptions}
      textOptions={{ font_name: 'Inter.ttf', gravity: 'south', break_symbols: [] } as unknown as TextOptions}
      jpegQuality={90}
      onOverlayChange={vi.fn()}
      onTextChange={vi.fn()}
      onQualityChange={vi.fn()}
      onReset={vi.fn()}
      onClose={vi.fn()}
    />
  );
  return onTitleChange;
}

describe('PosterEditPanel title', () => {
  it('keeps the line breaks typed into the title', () => {
    const onTitleChange = renderPanel('The Lord of the Rings');

    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: 'The Lord\nof the\nRings' },
    });

    expect(onTitleChange).toHaveBeenCalledWith('The Lord\nof the\nRings');
  });

  it('shows a multi-line title as the lines it will be drawn on', () => {
    renderPanel('The Lord\n\nof the Rings');

    expect(screen.getByLabelText('Title')).toHaveValue('The Lord\n\nof the Rings');
  });
});
