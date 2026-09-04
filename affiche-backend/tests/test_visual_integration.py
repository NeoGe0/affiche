import pytest
from pathlib import Path
from PIL import Image

from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.model.text_options import TextOptions
from affiche.app.image.overlay_generator import OverlayGenerator
from affiche.app.image.text_renderer import TextRenderer
from affiche.app.image.image_composer import ImageComposer
from affiche.app.image.poster_decorator_service import PosterDecorationService

OUTPUT_DIR = Path(__file__).parent / "output"

@pytest.fixture(autouse=True)
def setup_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class TestVisualOverlay:

    def test_overlay_with_border_and_glow(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            border_enabled=True,
            border_px=30,
            border_color="#000000",
            inner_glow_strength=0.3,
            inner_glow_color="#000000",
        )

        overlay = generator.generate_overlay(options)

        output_path = OUTPUT_DIR / "overlay_border_glow.png"
        overlay.save(output_path, "PNG")

        assert output_path.exists()
        print(f"\nSaved: {output_path}")

    def test_overlay_with_gradient(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            matte_height_ratio=0.1,
            fade_height_ratio=0.3,
            gradient_color="#000000",
        )

        overlay = generator.generate_overlay(options)

        output_path = OUTPUT_DIR / "overlay_gradient.png"
        overlay.save(output_path, "PNG")

        assert output_path.exists()
        print(f"\nSaved: {output_path}")

    def test_overlay_full_effects(self):
        generator = OverlayGenerator()
        options = OverlayOptions(
            border_enabled=True,
            border_px=30,
            border_color="#000000",
            inner_glow_strength=0.3,
            inner_glow_color="#000000",
            matte_height_ratio=0.05,
            fade_height_ratio=0.25,
            gradient_color="#000000",
            vignette_strength=0.2,
            vignette_color="#000000",
        )

        overlay = generator.generate_overlay(options)

        output_path = OUTPUT_DIR / "overlay_full.png"
        overlay.save(output_path, "PNG")

        assert output_path.exists()
        print(f"\nSaved: {output_path}")

class TestVisualTextRendering:

    def test_text_short_title(self):
        image = Image.new("RGBA", (2000, 3000), (30, 30, 50, 255))
        renderer = TextRenderer()
        options = TextOptions(
            font_color="#FFFFFF",
            all_caps=True,
            min_font_ratio=0.015,
            max_font_ratio=0.1,
            text_offset_ratio=0.143,
            border_padding_ratio=0.015,
        )

        result = renderer.render_text(image, "Inception", options)

        output_path = OUTPUT_DIR / "text_short.png"
        result.save(output_path, "PNG")

        assert output_path.exists()
        print(f"\nSaved: {output_path}")

    def test_text_long_title(self):
        image = Image.new("RGBA", (2000, 3000), (30, 30, 50, 255))
        renderer = TextRenderer()
        options = TextOptions(
            font_color="#FFFFFF",
            all_caps=True,
            min_font_ratio=0.015,
            max_font_ratio=0.067,
            max_width_ratio=0.95,
            max_height_ratio=0.167,
            text_offset_ratio=0.143,
            border_padding_ratio=0.015,
            auto_wrap=True,
            auto_wrap_threshold_ratio=0.05,
        )

        result = renderer.render_text(
            image,
            "The Lord of the Rings: The Fellowship of the Ring",
            options
        )

        output_path = OUTPUT_DIR / "text_long.png"
        result.save(output_path, "PNG")

        assert output_path.exists()
        print(f"\nSaved: {output_path}")

    def test_text_with_symbol_break(self):
        image = Image.new("RGBA", (2000, 3000), (30, 30, 50, 255))
        renderer = TextRenderer()
        options = TextOptions(
            font_color="#FFFFFF",
            all_caps=True,
            text_offset_ratio=0.143,
            border_padding_ratio=0.015,
            break_on_symbols=True,
            break_symbols=[": "],
            line_spacing_ratio=0.1,
        )

        result = renderer.render_text(image, "The Matrix: Reloaded", options)

        output_path = OUTPUT_DIR / "text_symbol_break.png"
        result.save(output_path, "PNG")

        assert output_path.exists()
        print(f"\nSaved: {output_path}")

    def test_text_with_stroke(self):
        image = Image.new("RGBA", (2000, 3000), (100, 100, 120, 255))
        renderer = TextRenderer()
        options = TextOptions(
            font_color="#FFFFFF",
            all_caps=True,
            text_offset_ratio=0.143,
            border_padding_ratio=0.015,
            stroke_enabled=True,
            stroke_color="#000000",
            stroke_width_ratio=0.02,
        )

        result = renderer.render_text(image, "Avengers", options)

        output_path = OUTPUT_DIR / "text_stroke.png"
        result.save(output_path, "PNG")

        assert output_path.exists()
        print(f"\nSaved: {output_path}")

class TestVisualFullPoster:

    def test_full_poster_decoration(self):
        base_image = Image.new("RGBA", (2000, 3000), (50, 80, 100, 255))

        from PIL import ImageDraw
        draw = ImageDraw.Draw(base_image)
        draw.ellipse([700, 800, 1300, 1400], fill=(80, 100, 120, 255))

        overlay_options = OverlayOptions(
            border_enabled=True,
            border_px=30,
            border_color="#000000",
            inner_glow_strength=0.3,
            inner_glow_color="#000000",
            matte_height_ratio=0.05,
            fade_height_ratio=0.25,
            gradient_color="#000000",
        )

        text_options = TextOptions(
            font_color="#FFFFFF",
            all_caps=True,
            min_font_ratio=0.015,
            max_font_ratio=0.067,
            max_width_ratio=0.95,
            max_height_ratio=0.167,
            text_offset_ratio=0.143,
            border_padding_ratio=0.015,
            line_spacing_ratio=0.1,
            auto_wrap=True,
            auto_wrap_threshold_ratio=0.05,
        )

        service = PosterDecorationService(
            options=overlay_options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=ImageComposer(),
            text_renderer=TextRenderer(),
        )

        from io import BytesIO
        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        result_bytes = service.decorate_poster(image_bytes, "The Dark Knight")

        result_image = Image.open(BytesIO(result_bytes))
        output_path = OUTPUT_DIR / "poster_full.jpg"
        result_image.save(output_path, "JPEG", quality=90)

        assert output_path.exists()
        print(f"\nSaved: {output_path}")

    def test_poster_comparison_titles(self):
        titles = [
            "Inception",
            "The Matrix",
            "The Shawshank Redemption",
            "The Lord of the Rings: The Return of the King",
        ]

        overlay_options = OverlayOptions(
            border_enabled=True,
            border_px=30,
            border_color="#000000",
            inner_glow_strength=0.3,
            inner_glow_color="#000000",
            fade_height_ratio=0.4,
            gradient_color="#000000",
        )

        text_options = TextOptions(
            font_color="#FFFFFF",
            all_caps=True,
            min_font_ratio=0.015,
            max_font_ratio=0.067,
            max_width_ratio=0.95,
            max_height_ratio=0.167,
            text_offset_ratio=0.143,
            border_padding_ratio=0.015,
            line_spacing_ratio=0.1,
            auto_wrap=True,
            auto_wrap_threshold_ratio=0.05,
            break_on_symbols=True,
            break_symbols=[": ", " - "],
        )

        service = PosterDecorationService(
            options=overlay_options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=ImageComposer(),
            text_renderer=TextRenderer(),
        )

        from io import BytesIO

        for i, title in enumerate(titles):
            base_image = Image.new("RGBA", (2000, 3000), (40 + i*20, 50, 70, 255))
            buffer = BytesIO()
            base_image.save(buffer, format="PNG")

            result_bytes = service.decorate_poster(buffer.getvalue(), title)

            result_image = Image.open(BytesIO(result_bytes))
            safe_title = title.replace(":", "").replace(" ", "_")[:30]
            output_path = OUTPUT_DIR / f"poster_compare_{i}_{safe_title}.jpg"
            result_image.save(output_path, "JPEG", quality=90)

            print(f"\nSaved: {output_path}")

        assert True
