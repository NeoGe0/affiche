import { fontBaseName } from './fontName';

const SAMPLE_PX = 64;

export function glyphsAreIdentical(ctx: CanvasRenderingContext2D, family: string): boolean {
  const size = SAMPLE_PX * 2;
  ctx.canvas.width = size;
  ctx.canvas.height = size;

  const rasterise = (character: string): Uint8ClampedArray => {

    ctx.clearRect(0, 0, size, size);
    ctx.font = `${SAMPLE_PX}px "${family}"`;
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(character, 4, SAMPLE_PX + 4);
    return ctx.getImageData(0, 0, size, size).data;
  };

  const lower = rasterise('a');
  const upper = rasterise('A');
  if (lower.length !== upper.length) return false;

  let inked = false;
  for (let i = 3; i < lower.length; i += 4) {
    if (lower[i] !== 0) {
      inked = true;
      break;
    }
  }
  if (!inked) return false;

  for (let i = 0; i < lower.length; i += 1) {
    if (lower[i] !== upper[i]) return false;
  }
  return true;
}

export async function isCapsOnlyFont(fontFile: string): Promise<boolean> {
  const family = fontBaseName(fontFile);
  const spec = `${SAMPLE_PX}px "${family}"`;
  try {
    await document.fonts.load(spec);
  } catch {

    return false;
  }

  if (!document.fonts.check(spec)) return false;

  const ctx = document.createElement('canvas').getContext('2d');
  if (!ctx) return false;

  try {
    return glyphsAreIdentical(ctx, family);
  } catch {

    return false;
  }
}
