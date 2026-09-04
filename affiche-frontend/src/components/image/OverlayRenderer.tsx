import type { OverlayOptions } from "../../types"

export function drawOverlay(
  ctx: CanvasRenderingContext2D,
  o: OverlayOptions
) {
  applyVignette(ctx, o)
  applyGradientMatte(ctx, o)
  applyInnerGlow(ctx, o)
  applyGrain(ctx, o)

  applyBorder(ctx, o)

  if (o.show_text_area) {
    drawTextGuide(ctx, o)
  }
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "")
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function applyVignette(ctx: CanvasRenderingContext2D, o: OverlayOptions) {
  if (o.vignette_strength <= 0) return

  const { width, height } = ctx.canvas
  const g = ctx.createRadialGradient(
    width / 2,
    height / 2,
    Math.min(width, height) * 0.2,
    width / 2,
    height / 2,
    Math.max(width, height) * 0.8
  )

  g.addColorStop(0, "rgba(0,0,0,0)")
  g.addColorStop(1, hexToRgba(o.vignette_color, o.vignette_strength))

  ctx.fillStyle = g
  ctx.fillRect(0, 0, width, height)
}

function applyGradientMatte(ctx: CanvasRenderingContext2D, o: OverlayOptions) {
  if (o.matte_height_ratio <= 0 && o.fade_height_ratio <= 0) return

  const { width, height } = ctx.canvas

  const matteH = Math.floor(height * o.matte_height_ratio)
  const fadeH = Math.floor(height * o.fade_height_ratio)

  const startY = height - matteH - fadeH
  const g = ctx.createLinearGradient(0, startY, 0, height - matteH)
  g.addColorStop(0, hexToRgba(o.gradient_color, 0))
  g.addColorStop(1, hexToRgba(o.gradient_color, 1))

  if (fadeH > 0) {
    ctx.fillStyle = g
    ctx.fillRect(0, startY, width, fadeH)
  }

  if (matteH > 0) {
    ctx.fillStyle = o.gradient_color
    ctx.fillRect(0, height - matteH, width, matteH)
  }
}

function applyInnerGlow(ctx: CanvasRenderingContext2D, o: OverlayOptions) {
  if (o.inner_glow_strength <= 0) return

  const { width, height } = ctx.canvas
  const minDim = Math.min(width, height)

  const glowRadius = Math.floor(minDim * 0.2 * o.inner_glow_strength)
  if (glowRadius < 1) return

  const strength = o.inner_glow_strength

  const topGrad = ctx.createLinearGradient(0, 0, 0, glowRadius)
  topGrad.addColorStop(0, hexToRgba(o.inner_glow_color, strength))
  topGrad.addColorStop(1, hexToRgba(o.inner_glow_color, 0))
  ctx.fillStyle = topGrad
  ctx.fillRect(0, 0, width, glowRadius)

  const bottomGrad = ctx.createLinearGradient(0, height, 0, height - glowRadius)
  bottomGrad.addColorStop(0, hexToRgba(o.inner_glow_color, strength))
  bottomGrad.addColorStop(1, hexToRgba(o.inner_glow_color, 0))
  ctx.fillStyle = bottomGrad
  ctx.fillRect(0, height - glowRadius, width, glowRadius)

  const leftGrad = ctx.createLinearGradient(0, 0, glowRadius, 0)
  leftGrad.addColorStop(0, hexToRgba(o.inner_glow_color, strength))
  leftGrad.addColorStop(1, hexToRgba(o.inner_glow_color, 0))
  ctx.fillStyle = leftGrad
  ctx.fillRect(0, 0, glowRadius, height)

  const rightGrad = ctx.createLinearGradient(width, 0, width - glowRadius, 0)
  rightGrad.addColorStop(0, hexToRgba(o.inner_glow_color, strength))
  rightGrad.addColorStop(1, hexToRgba(o.inner_glow_color, 0))
  ctx.fillStyle = rightGrad
  ctx.fillRect(width - glowRadius, 0, glowRadius, height)
}

function applyGrain(ctx: CanvasRenderingContext2D, o: OverlayOptions) {
  if (o.grain_amount <= 0) return

  const { width, height } = ctx.canvas

  const scaleFactor = Math.max(0.5, o.grain_size)
  const noiseW = Math.max(1, Math.floor(width / scaleFactor))
  const noiseH = Math.max(1, Math.floor(height / scaleFactor))

  const noiseCanvas = document.createElement("canvas")
  noiseCanvas.width = noiseW
  noiseCanvas.height = noiseH
  const noiseCtx = noiseCanvas.getContext("2d")!

  const imageData = noiseCtx.createImageData(noiseW, noiseH)
  const data = imageData.data
  const maxAlpha = Math.floor(255 * o.grain_amount)

  for (let i = 0; i < data.length; i += 4) {
    const alpha = Math.floor(Math.random() * maxAlpha)
    data[i] = 0
    data[i + 1] = 0
    data[i + 2] = 0
    data[i + 3] = alpha
  }

  noiseCtx.putImageData(imageData, 0, 0)

  ctx.imageSmoothingEnabled = false
  ctx.drawImage(noiseCanvas, 0, 0, width, height)
  ctx.imageSmoothingEnabled = true
}

function applyBorder(ctx: CanvasRenderingContext2D, o: OverlayOptions) {
  if (!o.border_enabled || o.border_px <= 0) return

  const { width, height } = ctx.canvas
  const minDim = Math.min(width, height)

  const outerRadius = Math.floor(minDim * 0.5 * o.corner_radius)
  const borderWidth = o.border_px

  ctx.strokeStyle = o.border_color
  ctx.lineWidth = borderWidth * 2

  if (outerRadius > 0) {
    drawRoundedRect(ctx, 0, 0, width, height, outerRadius)
  } else {
    ctx.strokeRect(0, 0, width, height)
  }
}

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.arcTo(x + w, y, x + w, y + r, r)
  ctx.lineTo(x + w, y + h - r)
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r)
  ctx.lineTo(x + r, y + h)
  ctx.arcTo(x, y + h, x, y + h - r, r)
  ctx.lineTo(x, y + r)
  ctx.arcTo(x, y, x + r, y, r)
  ctx.closePath()
  ctx.stroke()
}

function drawTextGuide(ctx: CanvasRenderingContext2D, o: OverlayOptions) {
  if (o.text_box_w <= 0 || o.text_box_h <= 0) return

  const { width, height } = ctx.canvas

  const x1 = Math.floor((width - o.text_box_w) / 2)
  const y2 = height - o.text_box_offset
  const y1 = y2 - o.text_box_h

  ctx.fillStyle = "rgba(255, 0, 0, 0.3)"
  ctx.fillRect(x1, y1, o.text_box_w, o.text_box_h)

  ctx.strokeStyle = "rgba(255, 0, 0, 1)"
  ctx.lineWidth = 3
  ctx.strokeRect(x1, y1, o.text_box_w, o.text_box_h)
}
