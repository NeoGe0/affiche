import hashlib
from collections import OrderedDict
from io import BytesIO
from threading import Lock
from typing import Optional, Union

from PIL import Image

from affiche.app.image.image_composer import ImageComposer
from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.model.text_options import TextOptions
from affiche.app.image.overlay_generator import OverlayGenerator
from affiche.app.image.text_renderer import TextRenderer

class PosterDecorationService:

    _OVERLAY_CACHE_SIZE = 4

    def __init__(self,
                 options: OverlayOptions,
                 text_options: TextOptions,
                 generator: OverlayGenerator,
                 composer: ImageComposer,
                 text_renderer: TextRenderer,
                 jpeg_quality: int = 90):
        self._generator = generator
        self._composer = composer
        self._text_renderer = text_renderer
        self._options = options
        self._text_options = text_options
        self._jpeg_quality = jpeg_quality
        self._overlay_cache: "OrderedDict[str, Image.Image]" = OrderedDict()
        self._overlay_lock = Lock()

    def _overlay_for(self, options: OverlayOptions) -> Image.Image:
        key = options.model_dump_json()
        with self._overlay_lock:
            cached = self._overlay_cache.get(key)
            if cached is not None:
                self._overlay_cache.move_to_end(key)
                return cached

            overlay = self._generator.generate_overlay(options)
            self._overlay_cache[key] = overlay
            while len(self._overlay_cache) > self._OVERLAY_CACHE_SIZE:
                self._overlay_cache.popitem(last=False)
            return overlay

    UNSTYLED_FINGERPRINT = "unstyled"

    def style_fingerprint(
            self,
            overlay_options: Optional[OverlayOptions] = None,
            text_options: Optional[TextOptions] = None,
            apply_style: bool = True
    ) -> str:
        if not apply_style:
            return self.UNSTYLED_FINGERPRINT

        effective_overlay = overlay_options if overlay_options is not None else self._options
        effective_text = text_options if text_options is not None else self._text_options
        payload = "\n".join([
            effective_overlay.model_dump_json(),
            effective_text.model_dump_json() if effective_text else "",
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def decorate_poster(
            self,
            image_url: Union[str, bytes],
            title: str,
            output_format: str = "JPEG",
            jpeg_quality: Optional[int] = None,
            overlay_options: Optional[OverlayOptions] = None,
            text_options: Optional[TextOptions] = None,
            apply_style: bool = True
    ) -> bytes:
        if not apply_style:
            overlay = None
        else:
            overlay = self._overlay_for(
                overlay_options if overlay_options is not None else self._options
            )
        result = self._composer.apply_overlay_to_image(image_url, overlay)

        effective_text = text_options if text_options is not None else self._text_options
        if apply_style and effective_text and effective_text.enabled and title:
            result = self._text_renderer.render_text(result, title, effective_text)

        if output_format.upper() == "JPEG" and result.mode == "RGBA":
            background = Image.new("RGB", result.size, (0, 0, 0))
            background.paste(result, mask=result.split()[3])
            result = background

        output = BytesIO()
        quality = jpeg_quality if jpeg_quality is not None else self._jpeg_quality
        result.save(output, format=output_format, quality=quality)
        return output.getvalue()

    def reset_overlay(self):
        with self._overlay_lock:
            self._overlay_cache.clear()
