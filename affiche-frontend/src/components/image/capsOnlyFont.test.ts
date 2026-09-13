import { describe, it, expect, vi } from 'vitest';

import { glyphsAreIdentical, isCapsOnlyFont } from './capsOnlyFont';

function contextReturning(bitmaps: Record<string, number[]>) {
  let drawn = '';
  return {
    canvas: { width: 0, height: 0 },
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn((character: string) => {
      drawn = character;
    }),
    getImageData: vi.fn(() => ({
      data: Uint8ClampedArray.from(bitmaps[drawn] ?? []),
    })),
    font: '',
    fillStyle: '',
  } as unknown as CanvasRenderingContext2D;
}

const INKED = [255, 255, 255, 255, 0, 0, 0, 0];
const INKED_DIFFERENTLY = [255, 255, 255, 255, 255, 255, 255, 255];
const BLANK = [0, 0, 0, 0, 0, 0, 0, 0];

describe('glyphsAreIdentical', () => {
  it('reports a caps-only font when a and A rasterise the same', () => {
    const ctx = contextReturning({ a: INKED, A: INKED });

    expect(glyphsAreIdentical(ctx, 'BebasNeue-Regular')).toBe(true);
  });

  it('reports a normal font when the two differ', () => {
    const ctx = contextReturning({ a: INKED, A: INKED_DIFFERENTLY });

    expect(glyphsAreIdentical(ctx, 'PlayfairDisplay-Regular')).toBe(false);
  });

  it('refuses to answer from a blank canvas', () => {

    const ctx = contextReturning({ a: BLANK, A: BLANK });

    expect(glyphsAreIdentical(ctx, 'NotLoaded-Regular')).toBe(false);
  });

  it('sizes the canvas before measuring, since sizing resets the context', () => {
    const ctx = contextReturning({ a: INKED, A: INKED });

    glyphsAreIdentical(ctx, 'BebasNeue-Regular');

    expect(ctx.canvas.width).toBeGreaterThan(0);
    expect(ctx.canvas.height).toBeGreaterThan(0);

    expect(ctx.font).toContain('BebasNeue-Regular');
  });
});

describe('isCapsOnlyFont', () => {
  it('answers false where there is no font API to measure with', async () => {

    await expect(isCapsOnlyFont('BebasNeue-Regular.ttf')).resolves.toBe(false);
  });
});
