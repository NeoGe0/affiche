import type { TextOptions } from "../../types"
import { fontBaseName } from "./fontName"
import { wrapVariants } from "./textWrap"

function fontFamily(fontName: string): string {
  return `"${fontBaseName(fontName)}", "Bebas Neue", "Impact", "Arial Black", sans-serif`
}

const BLANK_LINE_RATIO = 0.5

function lineHeightOf(ctx: CanvasRenderingContext2D, line: string, fontSize: number): number {
  if (!line) return Math.floor(fontSize * BLANK_LINE_RATIO)
  const metrics = ctx.measureText(line)

  return metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent
}

function measureTextBox(
  ctx: CanvasRenderingContext2D,
  lines: string[],
  lineSpacing: number,
  fontSize: number
): { width: number; height: number } {
  let maxWidth = 0
  let totalHeight = 0

  for (let i = 0; i < lines.length; i++) {
    const metrics = ctx.measureText(lines[i])

    maxWidth = Math.max(maxWidth, metrics.width)
    totalHeight += lineHeightOf(ctx, lines[i], fontSize)
    if (i < lines.length - 1) {
      totalHeight += lineSpacing
    }
  }

  return { width: maxWidth, height: totalHeight }
}

function textFits(
  ctx: CanvasRenderingContext2D,
  text: string,
  size: number,
  o: TextOptions,
  maxWidth: number,
  maxHeight: number
): boolean {
  ctx.font = `${size}px ${fontFamily(o.font_name)}`
  const lineSpacing = Math.trunc(size * o.line_spacing_ratio)
  const { width, height } = measureTextBox(ctx, text.split("\n"), lineSpacing, size)
  const stroke = o.stroke_enabled ? Math.floor(size * o.stroke_width_ratio) : 0

  return width + 2 * stroke <= maxWidth && height + 2 * stroke <= maxHeight
}

function largestFittingSize(
  ctx: CanvasRenderingContext2D,
  text: string,
  o: TextOptions,
  lo: number,
  hi: number,
  maxWidth: number,
  maxHeight: number
): number {
  let best = 0

  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2)
    if (textFits(ctx, text, mid, o, maxWidth, maxHeight)) {
      best = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }

  return best
}

function findOptimalFontSize(
  ctx: CanvasRenderingContext2D,
  text: string,
  o: TextOptions,
): number {
  const { width: canvasWidth, height: canvasHeight } = ctx.canvas

  const preferredMin = Math.max(1, Math.floor(canvasHeight * o.min_font_ratio))
  const maxSize = Math.floor(canvasHeight * o.max_font_ratio)
  const maxWidth = Math.floor(canvasWidth * o.max_width_ratio)
  const maxHeight = Math.floor(canvasHeight * o.max_height_ratio)
  const padding = Math.floor(
    Math.min(canvasWidth, canvasHeight) * o.border_padding_ratio
  )

  const safeWidth = canvasWidth - 2 * padding
  const safeHeight = canvasHeight - 2 * padding
  const effectiveMaxWidth = Math.min(maxWidth, safeWidth)
  const effectiveMaxHeight = Math.min(maxHeight, safeHeight)

  const best = largestFittingSize(
    ctx, text, o, preferredMin, maxSize, effectiveMaxWidth, effectiveMaxHeight
  )
  if (best > 0) return best

  return Math.max(
    1,
    largestFittingSize(
      ctx, text, o, 1, preferredMin - 1, effectiveMaxWidth, effectiveMaxHeight
    )
  )
}

function findBestWrap(
  ctx: CanvasRenderingContext2D,
  text: string,
  o: TextOptions
): string {
  let bestVariant = text
  let bestFontSize = 0

  for (const variant of wrapVariants(text)) {
    const fontSize = findOptimalFontSize(ctx, variant, o)
    if (fontSize > bestFontSize) {
      bestFontSize = fontSize
      bestVariant = variant
    }
  }

  return bestVariant
}

function calculatePosition(
  ctx: CanvasRenderingContext2D,
  lines: string[],
  fontSize: number,
  o: TextOptions
): { x: number; y: number } {
  const { width: canvasWidth, height: canvasHeight } = ctx.canvas

  const padding = Math.floor(
    Math.min(canvasWidth, canvasHeight) * o.border_padding_ratio
  )
  const textOffset = Math.floor(canvasHeight * o.text_offset_ratio)
  const lineSpacing = Math.trunc(fontSize * o.line_spacing_ratio)

  const { width: textWidth, height: textHeight } = measureTextBox(
    ctx,
    lines,
    lineSpacing,
    fontSize
  )

  const safeWidth = canvasWidth - 2 * padding
  const x = padding + Math.floor((safeWidth - textWidth) / 2)

  let y: number
  if (o.gravity === "south") {
    const textBottomY = canvasHeight - padding - textOffset
    y = textBottomY - textHeight
  } else if (o.gravity === "north") {
    y = padding + textOffset
  } else {

    const safeHeight = canvasHeight - 2 * padding
    y = padding + Math.floor((safeHeight - textHeight) / 2)
  }

  y = Math.max(padding, y)

  return { x, y }
}

export function drawText(
  ctx: CanvasRenderingContext2D,
  text: string,
  o: TextOptions
) {
  if (!text.trim()) return

  let displayText = text.trim()
  if (o.all_caps) displayText = displayText.toUpperCase()

  if (o.break_on_symbols) {
    for (const s of o.break_symbols) {
      displayText = displayText.replaceAll(s, "\n")
    }
  }

  let fontSize = findOptimalFontSize(ctx, displayText, o)

  const autoWrapThreshold = Math.floor(ctx.canvas.height * o.auto_wrap_threshold_ratio)
  if (o.auto_wrap && fontSize < autoWrapThreshold) {
    displayText = findBestWrap(ctx, displayText, o)
    fontSize = findOptimalFontSize(ctx, displayText, o)
  }

  ctx.font = `${fontSize}px ${fontFamily(o.font_name)}`
  ctx.textBaseline = "top"

  const lines = displayText.split("\n")
  const lineSpacing = Math.trunc(fontSize * o.line_spacing_ratio)
  const strokeWidth = Math.floor(fontSize * o.stroke_width_ratio)
  const { y } = calculatePosition(ctx, lines, fontSize, o)

  const padding = Math.floor(
    Math.min(ctx.canvas.width, ctx.canvas.height) * o.border_padding_ratio
  )
  const safeWidth = ctx.canvas.width - 2 * padding

  let cursorY = y

  for (const line of lines) {
    const metrics = ctx.measureText(line)

    const lineX = padding + Math.floor((safeWidth - metrics.width) / 2)
    const lineHeight = lineHeightOf(ctx, line, fontSize)

    if (o.stroke_enabled && strokeWidth > 0) {
      ctx.lineWidth = strokeWidth
      ctx.strokeStyle = o.stroke_color
      ctx.strokeText(line, lineX, cursorY)
    }

    ctx.fillStyle = o.font_color
    ctx.fillText(line, lineX, cursorY)

    cursorY += lineHeight + lineSpacing
  }
}
