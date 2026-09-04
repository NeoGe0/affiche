import { useEffect, useRef, useState } from "react"
import type { OverlayOptions } from "../../types"
import type { TextOptions } from "../../types"
import { drawPoster } from "./PosterRenderer"
import styles from "./PosterPreview.module.css"

type Props = {
  imageUrl: string
  title?: string
  overlayOptions: OverlayOptions
  textOptions?: TextOptions
}

export function PosterPreview({
  imageUrl,
  title,
  overlayOptions,
  textOptions
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [prevArgs, setPrevArgs] = useState({ imageUrl, title, overlayOptions, textOptions })

  if (
    prevArgs.imageUrl !== imageUrl ||
    prevArgs.title !== title ||
    prevArgs.overlayOptions !== overlayOptions ||
    prevArgs.textOptions !== textOptions
  ) {
    setPrevArgs({ imageUrl, title, overlayOptions, textOptions })
    setIsLoading(true)
    setError(null)
  }

  useEffect(() => {
    if (!canvasRef.current) return

    let cancelled = false

    drawPoster(
      canvasRef.current,
      { imageUrl, title, overlayOptions, textOptions },
      () => cancelled
    )
      .then(() => {
        if (!cancelled) setIsLoading(false)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message || "Failed to load image")
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [imageUrl, title, overlayOptions, textOptions])

  return (
    <div className={styles.wrapper}>
      {
}
      <canvas
        ref={canvasRef}
        width={2000}
        height={3000}
        className={`${styles.canvas} ${error ? styles.canvasHidden : ""}`}
      />
      {isLoading && !error && (
        <div className={styles.loading}>Loading preview...</div>
      )}
      {error && (
        <div className={styles.error}>
          Preview unavailable
          <br />
          (CORS restriction)
        </div>
      )}
    </div>
  )
}
