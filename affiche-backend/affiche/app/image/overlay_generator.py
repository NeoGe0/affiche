from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np
from typing import Tuple

from affiche.app.image.model.overlay_options import OverlayOptions

class OverlayGenerator:
    POSTER_SIZE = (2000, 3000)
    BACKGROUND_SIZE = (3840, 2160)

    BLUR_DOWNSCALE_THRESHOLD = 10.0
    BLUR_DOWNSCALE_FACTOR = 4

    INNER_GLOW_RADIUS_RATIO = 0.2
    INNER_GLOW_INSET_MULTIPLIER = 1.5

    def __init__(self, random_seed: int | None = None):

        self.random_seed = random_seed
        if random_seed is not None:
            np.random.seed(random_seed)

    def generate_overlay(self, options: OverlayOptions) -> Image.Image:

        canvas = self._create_canvas(options)

        canvas = self._apply_vignette(canvas, options)
        canvas = self._apply_gradient_matte(canvas, options)
        canvas = self._apply_inner_glow(canvas, options)
        canvas = self._apply_grain(canvas, options)
        canvas = self._apply_blur(canvas, options)
        canvas = self._apply_border(canvas, options)

        if options.show_text_area:
            canvas = self._apply_text_area_guide(canvas, options)

        return canvas

    def _create_canvas(self, options: OverlayOptions) -> Image.Image:

        if options.overlay_type == "background":
            size = self.BACKGROUND_SIZE
        else:
            size = self.POSTER_SIZE

        return Image.new("RGBA", size, (0, 0, 0, 0))

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:

        h = hex_color.lstrip("#")
        if len(h) != 6:
            return (0, 0, 0)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _create_color_layer(self, size: Tuple[int, int], hex_color: str) -> Image.Image:

        rgb = self._hex_to_rgb(hex_color)
        return Image.new("RGBA", size, (*rgb, 255))

    def _apply_vignette(self, canvas: Image.Image, options: OverlayOptions) -> Image.Image:

        if options.vignette_strength <= 0:
            return canvas

        width, height = canvas.size

        grad_w, grad_h = width // 4, height // 4
        X, Y = np.meshgrid(np.linspace(-1, 1, grad_w), np.linspace(-1, 1, grad_h))
        radius = np.sqrt(X ** 2 + Y ** 2)
        radius = np.clip(radius, 0, 1)

        mask_data = (radius * 255 * options.vignette_strength).astype(np.uint8)
        vignette_mask = Image.fromarray(mask_data, mode="L")
        vignette_mask = vignette_mask.resize((width, height), Image.Resampling.BICUBIC)

        color_layer = self._create_color_layer(canvas.size, options.vignette_color)
        color_layer.putalpha(vignette_mask)

        return Image.alpha_composite(canvas, color_layer)

    def _apply_gradient_matte(self, canvas: Image.Image, options: OverlayOptions) -> Image.Image:

        if options.matte_height_ratio <= 0 and options.fade_height_ratio <= 0:
            return canvas

        width, height = canvas.size

        gradient_layer = self._create_color_layer(canvas.size, options.gradient_color)
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)

        matte_h_px = int(height * options.matte_height_ratio)
        fade_h_px = int(height * options.fade_height_ratio)

        if matte_h_px > 0:
            draw.rectangle(
                [0, height - matte_h_px, width, height],
                fill=255
            )

        if fade_h_px > 0:
            start_y = height - matte_h_px - fade_h_px
            for y in range(fade_h_px):
                alpha = int(255 * (y / fade_h_px))
                draw.line(
                    [(0, start_y + y), (width, start_y + y)],
                    fill=alpha
                )

        gradient_layer.putalpha(mask)
        return Image.alpha_composite(canvas, gradient_layer)

    def _apply_inner_glow(self, canvas: Image.Image, options: OverlayOptions) -> Image.Image:

        if options.inner_glow_strength <= 0:
            return canvas

        width, height = canvas.size
        min_dim = min(width, height)

        blur_radius = int(min_dim * self.INNER_GLOW_RADIUS_RATIO * options.inner_glow_strength)
        if blur_radius < 1:
            blur_radius = 1

        mask = Image.new("L", (width, height), 255)
        draw = ImageDraw.Draw(mask)
        inset = blur_radius * self.INNER_GLOW_INSET_MULTIPLIER
        draw.rectangle(
            [inset, inset, width - inset, height - inset],
            fill=0
        )
        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

        glow_layer = self._create_color_layer(canvas.size, options.inner_glow_color)
        glow_layer.putalpha(mask)

        return Image.alpha_composite(canvas, glow_layer)

    def _apply_grain(self, canvas: Image.Image, options: OverlayOptions) -> Image.Image:

        if options.grain_amount <= 0:
            return canvas

        width, height = canvas.size

        scale_factor = max(0.1, options.grain_size)
        noise_w = max(1, int(width / scale_factor))
        noise_h = max(1, int(height / scale_factor))

        max_alpha = int(255 * options.grain_amount)
        noise_mask = np.random.randint(0, max_alpha, (noise_h, noise_w), dtype=np.uint8)

        noise_mask_img = Image.fromarray(noise_mask, mode="L")
        noise_mask_img = noise_mask_img.resize((width, height), Image.Resampling.NEAREST)

        grain_layer = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        grain_layer.putalpha(noise_mask_img)

        return Image.alpha_composite(canvas, grain_layer)

    def _apply_blur(self, canvas: Image.Image, options: OverlayOptions) -> Image.Image:

        if options.blur_amount <= 0:
            return canvas

        if options.blur_amount > self.BLUR_DOWNSCALE_THRESHOLD:
            orig_size = canvas.size

            small_w = max(1, orig_size[0] // self.BLUR_DOWNSCALE_FACTOR)
            small_h = max(1, orig_size[1] // self.BLUR_DOWNSCALE_FACTOR)
            small_canvas = canvas.resize((small_w, small_h), Image.Resampling.BILINEAR)

            scaled_blur = options.blur_amount / self.BLUR_DOWNSCALE_FACTOR
            small_canvas = small_canvas.filter(ImageFilter.GaussianBlur(radius=scaled_blur))

            return small_canvas.resize(orig_size, Image.Resampling.BICUBIC)
        else:
            return canvas.filter(ImageFilter.GaussianBlur(radius=options.blur_amount))

    def _apply_border(self, canvas: Image.Image, options: OverlayOptions) -> Image.Image:

        if not options.border_enabled:
            return canvas

        width, height = canvas.size
        min_dim = min(width, height)

        outer_radius = int(min_dim * 0.5 * options.corner_radius)
        inner_radius = max(0, outer_radius - options.border_px)

        border_layer = self._create_color_layer(canvas.size, options.border_color)
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)

        if outer_radius > 0:
            draw.rounded_rectangle(
                [0, 0, width - 1, height - 1],
                radius=outer_radius,
                fill=255
            )
        else:
            draw.rectangle([0, 0, width, height], fill=255)

        if options.border_px > 0:
            ix0, iy0 = options.border_px, options.border_px
            ix1, iy1 = width - options.border_px - 1, height - options.border_px - 1

            if inner_radius > 0:
                draw.rounded_rectangle(
                    [ix0, iy0, ix1, iy1],
                    radius=inner_radius,
                    fill=0
                )
            else:
                draw.rectangle([ix0, iy0, ix1, iy1], fill=0)

        border_layer.putalpha(mask)
        canvas = Image.alpha_composite(canvas, border_layer)

        if outer_radius > 0:
            cutout_mask = Image.new("L", (width, height), 0)
            draw_cut = ImageDraw.Draw(cutout_mask)
            draw_cut.rounded_rectangle(
                [0, 0, width - 1, height - 1],
                radius=outer_radius,
                fill=255
            )

            r, g, b, a = canvas.split()
            new_alpha = ImageChops.multiply(a, cutout_mask)
            canvas.putalpha(new_alpha)

        return canvas

    def _apply_text_area_guide(self, canvas: Image.Image, options: OverlayOptions) -> Image.Image:

        if options.text_box_w <= 0 or options.text_box_h <= 0:
            return canvas

        width, height = canvas.size

        x1 = (width - options.text_box_w) // 2
        x2 = x1 + options.text_box_w
        y2 = height - options.text_box_offset
        y1 = y2 - options.text_box_h

        guide_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(guide_layer)
        draw.rectangle(
            [x1, y1, x2, y2],
            fill=(255, 0, 0, 80),
            outline=(255, 0, 0, 255),
            width=3
        )

        return Image.alpha_composite(canvas, guide_layer)
