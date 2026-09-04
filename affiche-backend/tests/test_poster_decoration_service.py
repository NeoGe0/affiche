import pytest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch
from io import BytesIO
from PIL import Image

from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.model.text_options import TextOptions
from affiche.app.image.poster_decorator_service import PosterDecorationService
from affiche.app.image.overlay_generator import OverlayGenerator
from affiche.app.image.image_composer import ImageComposer
from affiche.app.image.text_renderer import TextRenderer

class TestPosterDecorationServiceInit:

    def test_creates_with_all_components(self):
        overlay_options = OverlayOptions()
        text_options = TextOptions()
        generator = OverlayGenerator()
        composer = ImageComposer()
        renderer = TextRenderer()

        service = PosterDecorationService(
            options=overlay_options,
            text_options=text_options,
            generator=generator,
            composer=composer,
            text_renderer=renderer
        )

        assert service._options == overlay_options
        assert service._text_options == text_options
        assert service._generator is generator
        assert service._composer is composer
        assert service._text_renderer is renderer
        assert len(service._overlay_cache) == 0

class TestPosterDecorationServiceOverlay:

    def test_overlay_cached(self):
        options = OverlayOptions(border_enabled=True, border_px=10)
        service = PosterDecorationService(
            options=options,
            text_options=TextOptions(),
            generator=OverlayGenerator(),
            composer=ImageComposer(),
            text_renderer=TextRenderer()
        )

        overlay1 = service._overlay_for(options)
        overlay2 = service._overlay_for(options)

        assert overlay1 is overlay2

    def test_overlay_cached_per_options(self):
        default = OverlayOptions(border_enabled=True, border_px=10)
        service = PosterDecorationService(
            options=default,
            text_options=TextOptions(),
            generator=OverlayGenerator(),
            composer=ImageComposer(),
            text_renderer=TextRenderer()
        )
        other = OverlayOptions(border_enabled=True, border_px=25)

        first = service._overlay_for(default)
        second = service._overlay_for(other)

        assert first is not second
        assert service._overlay_for(default) is first
        assert service._overlay_for(other) is second

    def test_overlay_cache_is_bounded(self):
        service = PosterDecorationService(
            options=OverlayOptions(),
            text_options=TextOptions(),
            generator=OverlayGenerator(),
            composer=ImageComposer(),
            text_renderer=TextRenderer()
        )

        for px in range(service._OVERLAY_CACHE_SIZE + 3):
            service._overlay_for(OverlayOptions(border_enabled=True, border_px=px + 1))

        assert len(service._overlay_cache) == service._OVERLAY_CACHE_SIZE

    def test_overlay_generated_once_under_concurrency(self):
        options = OverlayOptions(border_enabled=True, border_px=10)
        generator = OverlayGenerator()
        calls = []
        real_generate = generator.generate_overlay

        def counting_generate(opts):
            calls.append(opts)
            return real_generate(opts)

        generator.generate_overlay = counting_generate
        service = PosterDecorationService(
            options=options,
            text_options=TextOptions(),
            generator=generator,
            composer=ImageComposer(),
            text_renderer=TextRenderer()
        )

        results = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            for overlay in pool.map(lambda _: service._overlay_for(options), range(4)):
                results.append(overlay)

        assert len(calls) == 1
        assert all(overlay is results[0] for overlay in results)

    def test_reset_overlay_clears_cache(self):
        options = OverlayOptions()
        service = PosterDecorationService(
            options=options,
            text_options=TextOptions(),
            generator=OverlayGenerator(),
            composer=ImageComposer(),
            text_renderer=TextRenderer()
        )

        overlay1 = service._overlay_for(options)
        service.reset_overlay()
        overlay2 = service._overlay_for(options)

        assert overlay1 is not overlay2

class TestPosterDecorationServiceDecorate:

    def test_decorate_returns_bytes(self):
        options = OverlayOptions()
        text_options = TextOptions()

        test_image = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        buffer = BytesIO()
        test_image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = test_image

        service = PosterDecorationService(
            options=options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=TextRenderer()
        )

        result = service.decorate_poster(image_bytes, "Test Title")

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_decorate_applies_overlay(self):
        options = OverlayOptions(border_enabled=True, border_px=30)
        text_options = TextOptions()

        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new(
            "RGBA", (2000, 3000), (255, 0, 0, 255)
        )

        service = PosterDecorationService(
            options=options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=TextRenderer()
        )

        test_image = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        buffer = BytesIO()
        test_image.save(buffer, format="PNG")

        service.decorate_poster(buffer.getvalue(), "Test")

        mock_composer.apply_overlay_to_image.assert_called_once()

    def test_decorate_applies_text_when_options_provided(self):
        overlay_options = OverlayOptions()
        text_options = TextOptions()

        mock_renderer = MagicMock()
        mock_renderer.render_text.return_value = Image.new(
            "RGBA", (2000, 3000), (255, 0, 0, 255)
        )

        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new(
            "RGBA", (2000, 3000), (255, 0, 0, 255)
        )

        service = PosterDecorationService(
            options=overlay_options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=mock_renderer
        )

        test_image = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        buffer = BytesIO()
        test_image.save(buffer, format="PNG")

        service.decorate_poster(buffer.getvalue(), "Test Title")

        mock_renderer.render_text.assert_called_once()

    def test_decorate_uses_per_call_text_options_override(self):
        override_text = TextOptions(text_offset_ratio=0.30, font_name="Override.ttf")

        mock_renderer = MagicMock()
        mock_renderer.render_text.return_value = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))

        service = PosterDecorationService(
            options=OverlayOptions(),
            text_options=TextOptions(text_offset_ratio=0.143, font_name="Base.ttf"),
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=mock_renderer,
        )

        service.decorate_poster(b"img", "Test Title", text_options=override_text)

        assert mock_renderer.render_text.call_args.args[2] is override_text

    def test_decorate_uses_per_call_overlay_override_bypassing_cache(self):
        mock_generator = MagicMock()
        mock_generator.generate_overlay.return_value = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new("RGBA", (10, 10), (0, 0, 0, 255))

        service = PosterDecorationService(
            options=OverlayOptions(),
            text_options=TextOptions(),
            generator=mock_generator,
            composer=mock_composer,
            text_renderer=MagicMock(),
        )

        override_overlay = OverlayOptions(border_enabled=True, border_px=25)
        service.decorate_poster(b"img", "Title", overlay_options=override_overlay)

        mock_generator.generate_overlay.assert_called_once_with(override_overlay)

    def test_decorate_uses_shared_defaults_when_no_override(self):
        text_options = TextOptions(text_offset_ratio=0.2)
        mock_renderer = MagicMock()
        mock_renderer.render_text.return_value = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new("RGBA", (10, 10), (0, 0, 0, 255))

        service = PosterDecorationService(
            options=OverlayOptions(),
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=mock_renderer,
        )

        service.decorate_poster(b"img", "Title")

        assert mock_renderer.render_text.call_args.args[2] is text_options

    def test_decorate_skips_text_when_empty_title(self):
        overlay_options = OverlayOptions()
        text_options = TextOptions()

        mock_renderer = MagicMock()
        mock_renderer.render_text.return_value = Image.new(
            "RGBA", (2000, 3000), (255, 0, 0, 255)
        )

        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new(
            "RGBA", (2000, 3000), (255, 0, 0, 255)
        )

        service = PosterDecorationService(
            options=overlay_options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=mock_renderer
        )

        test_image = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        buffer = BytesIO()
        test_image.save(buffer, format="PNG")

        service.decorate_poster(buffer.getvalue(), "")

        mock_renderer.render_text.assert_not_called()

class TestPosterDecorationServiceOutputFormat:

    def test_jpeg_output(self):
        options = OverlayOptions()
        text_options = TextOptions()

        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new(
            "RGBA", (2000, 3000), (255, 0, 0, 255)
        )

        service = PosterDecorationService(
            options=options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=TextRenderer()
        )

        test_image = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        buffer = BytesIO()
        test_image.save(buffer, format="PNG")

        result = service.decorate_poster(
            buffer.getvalue(),
            "Test",
            output_format="JPEG"
        )

        result_image = Image.open(BytesIO(result))
        assert result_image.format == "JPEG"

    def test_png_output(self):
        options = OverlayOptions()
        text_options = TextOptions()

        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new(
            "RGBA", (2000, 3000), (255, 0, 0, 255)
        )

        service = PosterDecorationService(
            options=options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=TextRenderer()
        )

        test_image = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        buffer = BytesIO()
        test_image.save(buffer, format="PNG")

        result = service.decorate_poster(
            buffer.getvalue(),
            "Test",
            output_format="PNG"
        )

        result_image = Image.open(BytesIO(result))
        assert result_image.format == "PNG"

    def test_jpeg_converts_rgba_to_rgb(self):
        options = OverlayOptions()
        text_options = TextOptions()

        mock_composer = MagicMock()
        mock_composer.apply_overlay_to_image.return_value = Image.new(
            "RGBA", (2000, 3000), (255, 0, 0, 255)
        )

        service = PosterDecorationService(
            options=options,
            text_options=text_options,
            generator=OverlayGenerator(),
            composer=mock_composer,
            text_renderer=TextRenderer()
        )

        test_image = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        buffer = BytesIO()
        test_image.save(buffer, format="PNG")

        result = service.decorate_poster(
            buffer.getvalue(),
            "Test",
            output_format="JPEG"
        )

        result_image = Image.open(BytesIO(result))
        assert result_image.mode == "RGB"
