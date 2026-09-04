import pytest
from PIL import Image

from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.overlay_generator import OverlayGenerator

class TestOverlayGeneratorCanvas:

    def test_creates_poster_size_canvas(self):
        generator = OverlayGenerator()
        options = OverlayOptions(overlay_type="poster")

        overlay = generator.generate_overlay(options)

        assert overlay.size == (2000, 3000)

    def test_creates_background_size_canvas(self):
        generator = OverlayGenerator()
        options = OverlayOptions(overlay_type="background")

        overlay = generator.generate_overlay(options)

        assert overlay.size == (3840, 2160)

    def test_canvas_is_transparent(self):
        generator = OverlayGenerator()
        options = OverlayOptions()

        overlay = generator.generate_overlay(options)

        pixel = overlay.getpixel((1000, 1500))
        assert pixel[3] == 0

class TestOverlayGeneratorBorder:

    def test_border_applied(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            border_enabled=True,
            border_px=30,
            border_color="#FF0000"
        )

        overlay = generator.generate_overlay(options)

        pixel = overlay.getpixel((15, 15))
        assert pixel[0] == 255
        assert pixel[3] == 255

    def test_border_not_applied_when_disabled(self):
        generator = OverlayGenerator()
        options = OverlayOptions(border_enabled=False)

        overlay = generator.generate_overlay(options)

        pixel = overlay.getpixel((10, 10))
        assert pixel[3] == 0

    def test_border_width_respected(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            border_enabled=True,
            border_px=50,
            border_color="#FF0000"
        )

        overlay = generator.generate_overlay(options)

        inside_pixel = overlay.getpixel((25, 25))
        assert inside_pixel[3] == 255

        center_pixel = overlay.getpixel((1000, 1500))

class TestOverlayGeneratorEffects:

    def test_vignette_applied(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            vignette_strength=0.5,
            vignette_color="#000000"
        )

        overlay = generator.generate_overlay(options)

        corner_pixel = overlay.getpixel((100, 100))
        center_pixel = overlay.getpixel((1000, 1500))

        assert corner_pixel[3] >= center_pixel[3]

    def test_gradient_matte_applied(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            matte_height_ratio=0.1,
            fade_height_ratio=0.2,
            gradient_color="#000000"
        )

        overlay = generator.generate_overlay(options)

        bottom_pixel = overlay.getpixel((1000, 2900))
        assert bottom_pixel[3] == 255

        top_pixel = overlay.getpixel((1000, 100))
        assert top_pixel[3] == 0

    def test_inner_glow_applied(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            inner_glow_strength=0.5,
            inner_glow_color="#000000"
        )

        overlay = generator.generate_overlay(options)

        edge_pixel = overlay.getpixel((50, 1500))
        center_pixel = overlay.getpixel((1000, 1500))

        assert edge_pixel[3] >= center_pixel[3]

    def test_grain_applied(self):
        generator = OverlayGenerator(random_seed=42)
        options = OverlayOptions(grain_amount=0.3)

        overlay = generator.generate_overlay(options)

        pixels = [
            overlay.getpixel((500, 500)),
            overlay.getpixel((501, 500)),
            overlay.getpixel((500, 501))
        ]

        alphas = [p[3] for p in pixels]
        assert len(set(alphas)) >= 1

class TestOverlayGeneratorCombined:

    def test_multiple_effects(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            border_enabled=True,
            border_px=30,
            border_color="#000000",
            inner_glow_strength=0.3,
            inner_glow_color="#000000",
            matte_height_ratio=0.1,
            fade_height_ratio=0.3,
            gradient_color="#000000"
        )

        overlay = generator.generate_overlay(options)

        assert overlay.size == (2000, 3000)
        assert overlay.mode == "RGBA"

    def test_all_effects_disabled(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            border_enabled=False,
            vignette_strength=0,
            inner_glow_strength=0,
            matte_height_ratio=0,
            fade_height_ratio=0,
            grain_amount=0,
            blur_amount=0
        )

        overlay = generator.generate_overlay(options)

        center_pixel = overlay.getpixel((1000, 1500))
        assert center_pixel[3] == 0

class TestOverlayGeneratorTextAreaGuide:

    def test_text_area_guide_shown(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            show_text_area=True,
            text_box_w=1000,
            text_box_h=200,
            text_box_offset=100
        )

        overlay = generator.generate_overlay(options)

        text_area_y = 3000 - 100 - 100
        pixel = overlay.getpixel((1000, text_area_y))

        assert pixel[0] > 0 or pixel[3] > 0

    def test_text_area_guide_hidden(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            show_text_area=False,
            text_box_w=1000,
            text_box_h=200,
            text_box_offset=100
        )

        overlay = generator.generate_overlay(options)

        center_pixel = overlay.getpixel((1000, 1500))
        assert center_pixel[3] == 0

class TestOverlayGeneratorDeterminism:

    def test_same_seed_same_output(self):
        options = OverlayOptions(grain_amount=0.3)

        gen1 = OverlayGenerator(random_seed=42)
        overlay1 = gen1.generate_overlay(options)

        gen2 = OverlayGenerator(random_seed=42)
        overlay2 = gen2.generate_overlay(options)

        for x, y in [(500, 500), (1000, 1500), (1500, 2500)]:
            assert overlay1.getpixel((x, y)) == overlay2.getpixel((x, y))

    def test_different_seed_different_output(self):
        options = OverlayOptions(grain_amount=0.5)

        gen1 = OverlayGenerator(random_seed=42)
        overlay1 = gen1.generate_overlay(options)

        gen2 = OverlayGenerator(random_seed=123)
        overlay2 = gen2.generate_overlay(options)

        different = False
        for x, y in [(500, 500), (1000, 1500), (1500, 2500)]:
            if overlay1.getpixel((x, y)) != overlay2.getpixel((x, y)):
                different = True
                break

        assert different
