from typing import Callable, Optional
from PIL import Image
from io import BytesIO
import requests

from affiche.config.http_config import HTTP_TIMEOUT, MAX_POSTER_DOWNLOAD_BYTES

POSTER_ASPECT_RATIO = 2 / 3

class ImageComposer:

    def __init__(self, auth_headers_resolver: Optional[Callable[[str], dict]] = None):
        self._auth_headers_resolver = auth_headers_resolver

    def apply_overlay_to_image(self,
                               image_source,
                               overlay: Optional[Image.Image]) -> Image.Image:
        if isinstance(image_source, str):
            if image_source.startswith(('http://', 'https://')):
                headers = (self._auth_headers_resolver(image_source)
                           if self._auth_headers_resolver else None)
                base_image = Image.open(BytesIO(self._download_image(image_source, headers)))
            else:
                base_image = Image.open(image_source)
        elif isinstance(image_source, bytes):
            base_image = Image.open(BytesIO(image_source))
        else:
            raise ValueError("image_source must be URL, filepath, or bytes")

        base_image = base_image.convert("RGBA")

        base_image = self._crop_to_aspect(base_image, POSTER_ASPECT_RATIO)

        if overlay is None:
            return base_image

        if overlay.size != base_image.size:
            overlay = overlay.resize(base_image.size, Image.Resampling.LANCZOS)

        result = Image.alpha_composite(base_image, overlay)

        return result

    @staticmethod
    def _crop_to_aspect(image: Image.Image,
                        aspect: float = POSTER_ASPECT_RATIO,
                        tolerance: float = 0.01) -> Image.Image:
        w, h = image.size
        if w == 0 or h == 0:
            return image
        current = w / h
        if abs(current - aspect) <= tolerance:
            return image
        if current > aspect:
            new_w = max(1, round(h * aspect))
            left = (w - new_w) // 2
            return image.crop((left, 0, left + new_w, h))
        new_h = max(1, round(w / aspect))
        top = (h - new_h) // 2
        return image.crop((0, top, w, top + new_h))

    @staticmethod
    def _download_image(url: str, headers: Optional[dict] = None) -> bytes:
        with requests.get(url, timeout=HTTP_TIMEOUT, stream=True, headers=headers or None) as response:
            response.raise_for_status()
            chunks, total = [], 0
            for chunk in response.iter_content(8192):
                total += len(chunk)
                if total > MAX_POSTER_DOWNLOAD_BYTES:
                    raise ValueError(
                        f"Poster exceeds {MAX_POSTER_DOWNLOAD_BYTES}-byte cap: {url}"
                    )
                chunks.append(chunk)
            return b"".join(chunks)
