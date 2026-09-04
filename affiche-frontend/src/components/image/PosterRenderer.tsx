import type { OverlayOptions } from "../../types"
import type { TextOptions } from "../../types"
import { drawOverlay } from "./OverlayRenderer"
import { drawText } from "./TextRenderer"
import { fontBaseName } from "./fontName"
import { API_BASE } from "../../api/client"

type Args = {
  imageUrl: string
  title?: string
  overlayOptions: OverlayOptions
  textOptions?: TextOptions
}

function getProxiedUrl(url: string): string {

  if (url.startsWith('custom:')) {
    return `${API_BASE}/service/custom-poster/${url.slice('custom:'.length)}`
  }

  if (url.startsWith('http://') || url.startsWith('https://')) {
    return `${API_BASE}/service/image-proxy?url=${encodeURIComponent(url)}`
  }
  return url
}

export async function drawPoster(
  canvas: HTMLCanvasElement,
  { imageUrl, title, overlayOptions, textOptions }: Args,
  isStale: () => boolean = () => false
) {

  const img = new Image()
  img.crossOrigin = "anonymous"
  img.src = getProxiedUrl(imageUrl)
  await img.decode()

  if (title && textOptions?.enabled && textOptions.font_name) {
    try {
      await document.fonts.load(`64px "${fontBaseName(textOptions.font_name)}"`)
    } catch {}
  }

  if (isStale()) return

  const ctx = canvas.getContext("2d")!
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

  drawOverlay(ctx, overlayOptions)

  if (title && textOptions?.enabled) {
    drawText(ctx, title, textOptions)
  }
}
