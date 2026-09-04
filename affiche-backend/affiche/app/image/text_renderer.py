import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, List, Optional

from affiche.app.image.font_store import RESOURCES_DIR
from affiche.app.image.model.text_options import TextOptions
from affiche.config.env_config import USER_FONTS_DIR

logger = logging.getLogger(__name__)

DEFAULT_FONT = "Quintessential-Regular.ttf"

BLANK_LINE_RATIO = 0.5

class TextRenderer:

    def __init__(self, font_dirs: Optional[List[Path]] = None):
        self._font_dirs: List[Path] = font_dirs or [RESOURCES_DIR, Path(USER_FONTS_DIR)]
        self._font_cache: dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = h[0] * 2 + h[1] * 2 + h[2] * 2
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _resolve_font_path(self, font_name: str) -> Path:
        if not font_name:
            font_name = DEFAULT_FONT

        font_path = Path(font_name)
        if font_path.is_absolute() and font_path.exists():
            return font_path

        for directory in self._font_dirs:
            candidate = directory / font_name
            if candidate.exists():
                return candidate

        return font_path

    def _load_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        resolved_path = self._resolve_font_path(font_name)
        cache_key = (str(resolved_path), size)

        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        try:
            font = ImageFont.truetype(str(resolved_path), size)
        except (OSError, IOError):
            font = ImageFont.load_default(size)

        self._font_cache[cache_key] = font
        return font

    def _apply_line_breaks(self, text: str, options: TextOptions) -> str:
        if not options.break_on_symbols:
            return text

        result = text
        for symbol in options.break_symbols:
            result = result.replace(symbol, "\n")

        return result

    def _generate_word_wrap_variants(self, text: str, max_lines: int = 3) -> List[str]:
        if "\n" in text:
            return [text]

        words = text.split()
        if len(words) <= 1:
            return [text]

        variants = [text]

        if len(words) >= 2:
            for i in range(1, len(words)):
                line1 = " ".join(words[:i])
                line2 = " ".join(words[i:])
                variants.append(f"{line1}\n{line2}")

        if max_lines >= 3 and len(words) >= 3:
            for i in range(1, len(words) - 1):
                for j in range(i + 1, len(words)):
                    line1 = " ".join(words[:i])
                    line2 = " ".join(words[i:j])
                    line3 = " ".join(words[j:])
                    variants.append(f"{line1}\n{line2}\n{line3}")

        return variants

    def _find_best_wrap(
            self,
            text: str,
            options: TextOptions,
            image_size: Tuple[int, int]
    ) -> str:
        variants = self._generate_word_wrap_variants(text)

        best_variant = text
        best_font_size = 0

        for variant in variants:
            font_size = self._find_optimal_font_size(variant, options, image_size)
            if font_size > best_font_size:
                best_font_size = font_size
                best_variant = variant

        return best_variant

    def _line_height(self, draw: ImageDraw.ImageDraw, line: str, font: ImageFont.FreeTypeFont,
                     font_size: int) -> int:
        if not line:
            return int(font_size * BLANK_LINE_RATIO)
        bbox = draw.textbbox((0, 0), line, font=font, anchor="lt")
        return bbox[3] - bbox[1]

    def _get_text_bbox(
            self,
            text: str,
            font: ImageFont.FreeTypeFont,
            line_spacing: int = 0,
            font_size: int = 0
    ) -> Tuple[int, int]:
        lines = text.split("\n")

        temp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(temp_img)

        max_width = 0
        total_height = 0

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font, anchor="lt")
            line_width = bbox[2] - bbox[0]
            line_height = self._line_height(draw, line, font, font_size or font.size)

            max_width = max(max_width, line_width)
            total_height += line_height

            if i < len(lines) - 1:
                total_height += line_spacing

        return max_width, total_height

    def _text_fits(
            self,
            text: str,
            size: int,
            options: TextOptions,
            max_width: int,
            max_height: int
    ) -> bool:
        font = self._load_font(options.font_name, size)
        line_spacing = int(size * options.line_spacing_ratio)
        width, height = self._get_text_bbox(text, font, line_spacing, size)
        stroke = int(size * options.stroke_width_ratio) if options.stroke_enabled else 0
        return (width + 2 * stroke) <= max_width and (height + 2 * stroke) <= max_height

    def _largest_fitting_size(
            self,
            text: str,
            options: TextOptions,
            lo: int,
            hi: int,
            max_width: int,
            max_height: int
    ) -> int:
        best = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._text_fits(text, mid, options, max_width, max_height):
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    def _find_optimal_font_size(
            self,
            text: str,
            options: TextOptions,
            image_size: Tuple[int, int]
    ) -> int:
        img_width, img_height = image_size

        preferred_min = max(1, int(img_height * options.min_font_ratio))
        max_size = int(img_height * options.max_font_ratio)

        padding = int(min(img_width, img_height) * options.border_padding_ratio)

        max_width = int(img_width * options.max_width_ratio)
        max_height = int(img_height * options.max_height_ratio)

        safe_width = img_width - (2 * padding)
        safe_height = img_height - (2 * padding)

        effective_max_width = min(max_width, safe_width)
        effective_max_height = min(max_height, safe_height)

        best = self._largest_fitting_size(
            text, options, preferred_min, max_size, effective_max_width, effective_max_height
        )
        if best == 0:
            best = self._largest_fitting_size(
                text, options, 1, preferred_min - 1, effective_max_width, effective_max_height
            )

        return max(1, best)

    def _calculate_text_position(
            self,
            image_size: Tuple[int, int],
            text_size: Tuple[int, int],
            options: TextOptions
    ) -> Tuple[int, int]:
        img_width, img_height = image_size
        text_width, text_height = text_size

        padding = int(min(img_width, img_height) * options.border_padding_ratio)

        text_offset = int(img_height * options.text_offset_ratio)

        safe_width = img_width - (2 * padding)

        x = padding + (safe_width - text_width) // 2

        if options.gravity == "south":
            text_bottom_y = img_height - padding - text_offset
            y = text_bottom_y - text_height
        elif options.gravity == "north":
            y = padding + text_offset
        else:
            safe_height = img_height - (2 * padding)
            y = padding + (safe_height - text_height) // 2

        x = max(padding, min(x, img_width - padding - text_width))

        y = max(padding, y)

        return x, y

    def render_text(
            self,
            image: Image.Image,
            text: str,
            options: TextOptions
    ) -> Image.Image:
        if not text or not text.strip():
            return image

        img_width, img_height = image.size

        display_text = text.strip()
        if options.all_caps:
            display_text = display_text.upper()

        display_text = self._apply_line_breaks(display_text, options)

        auto_wrap_threshold = int(img_height * options.auto_wrap_threshold_ratio)

        font_size = self._find_optimal_font_size(display_text, options, image.size)

        if options.auto_wrap and font_size < auto_wrap_threshold:
            display_text = self._find_best_wrap(display_text, options, image.size)
            font_size = self._find_optimal_font_size(display_text, options, image.size)

        font = self._load_font(options.font_name, font_size)

        line_spacing = int(font_size * options.line_spacing_ratio)
        stroke_width = int(font_size * options.stroke_width_ratio)

        text_width, text_height = self._get_text_bbox(
            display_text, font, line_spacing, font_size
        )
        x, y = self._calculate_text_position(
            image.size, (text_width, text_height), options
        )

        if image.mode != "RGBA":
            image = image.convert("RGBA")

        text_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        font_color = self._hex_to_rgb(options.font_color)
        stroke_color = self._hex_to_rgb(options.stroke_color) if options.stroke_enabled else None

        padding = int(min(img_width, img_height) * options.border_padding_ratio)
        safe_width = img_width - (2 * padding)

        lines = display_text.split("\n")
        current_y = y

        for line in lines:
            line_bbox = draw.textbbox((0, 0), line, font=font, anchor="lt")
            line_width = line_bbox[2] - line_bbox[0]
            line_height = self._line_height(draw, line, font, font_size)

            line_x = padding + (safe_width - line_width) // 2

            if options.stroke_enabled and stroke_width > 0:
                draw.text(
                    (line_x, current_y),
                    line,
                    font=font,
                    fill=(*stroke_color, 255),
                    stroke_width=stroke_width,
                    stroke_fill=(*stroke_color, 255),
                    anchor="lt"
                )

            draw.text(
                (line_x, current_y),
                line,
                font=font,
                fill=(*font_color, 255),
                anchor="lt"
            )

            current_y += line_height + line_spacing

        return Image.alpha_composite(image, text_layer)
