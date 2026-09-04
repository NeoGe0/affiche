import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

import { PosterPreview } from './PosterPreview';
import { drawPoster } from './PosterRenderer';
import type { OverlayOptions } from '../../types';

vi.mock('./PosterRenderer', () => ({ drawPoster: vi.fn() }));

const drawPosterMock = vi.mocked(drawPoster);

afterEach(() => {
  drawPosterMock.mockReset();
});

const overlay = { enabled: true } as unknown as OverlayOptions;

describe('PosterPreview', () => {
  it('shows the loading overlay while the draw is pending', () => {
    drawPosterMock.mockReturnValue(new Promise(() => {}));

    render(<PosterPreview imageUrl="/a.jpg" overlayOptions={overlay} />);

    expect(screen.getByText(/loading preview/i)).toBeInTheDocument();
  });

  it('clears the loading overlay once the draw resolves', async () => {
    drawPosterMock.mockResolvedValue(undefined);

    render(<PosterPreview imageUrl="/a.jpg" overlayOptions={overlay} />);

    await waitFor(() => expect(screen.queryByText(/loading preview/i)).not.toBeInTheDocument());
  });

  it('shows the unavailable message when the draw rejects', async () => {
    drawPosterMock.mockRejectedValue(new Error('tainted canvas'));

    render(<PosterPreview imageUrl="/a.jpg" overlayOptions={overlay} />);

    expect(await screen.findByText(/preview unavailable/i)).toBeInTheDocument();
  });

  it('clears a previous error when the inputs change', async () => {

    drawPosterMock.mockRejectedValueOnce(new Error('tainted canvas'));
    const { rerender } = render(<PosterPreview imageUrl="/bad.jpg" overlayOptions={overlay} />);
    expect(await screen.findByText(/preview unavailable/i)).toBeInTheDocument();

    drawPosterMock.mockResolvedValue(undefined);
    rerender(<PosterPreview imageUrl="/good.jpg" overlayOptions={overlay} />);

    await waitFor(() =>
      expect(screen.queryByText(/preview unavailable/i)).not.toBeInTheDocument()
    );
  });

  it('redraws when the overlay options change', async () => {
    drawPosterMock.mockResolvedValue(undefined);
    const { rerender } = render(<PosterPreview imageUrl="/a.jpg" overlayOptions={overlay} />);
    await waitFor(() => expect(drawPosterMock).toHaveBeenCalledOnce());

    rerender(
      <PosterPreview
        imageUrl="/a.jpg"
        overlayOptions={{ enabled: false } as unknown as OverlayOptions}
      />
    );

    await waitFor(() => expect(drawPosterMock).toHaveBeenCalledTimes(2));
  });
});
