import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from PIL import Image

from affiche.app.image.image_composer import ImageComposer
from affiche.config.http_config import HTTP_TIMEOUT, MAX_POSTER_DOWNLOAD_BYTES

class TestImageComposerInit:

    def test_creates_successfully(self):
        composer = ImageComposer()
        assert composer is not None

class TestImageComposerOverlay:

    def test_overlay_applied(self):
        composer = ImageComposer()

        base_image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 128))

        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        base_bytes = buffer.getvalue()

        result = composer.apply_overlay_to_image(base_bytes, overlay)

        pixel = result.getpixel((50, 50))
        assert pixel[0] < 255
        assert pixel[3] == 255

    def test_preserves_base_image_size(self):
        composer = ImageComposer()

        base_image = Image.new("RGBA", (800, 1200), (255, 0, 0, 255))
        overlay = Image.new("RGBA", (2000, 3000), (0, 0, 0, 128))

        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        base_bytes = buffer.getvalue()

        result = composer.apply_overlay_to_image(base_bytes, overlay)

        assert result.size == (800, 1200)

    def test_overlay_resized_to_match_base(self):
        composer = ImageComposer()

        base_image = Image.new("RGBA", (500, 750), (255, 0, 0, 255))
        overlay = Image.new("RGBA", (2000, 3000), (0, 0, 0, 128))

        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        base_bytes = buffer.getvalue()

        result = composer.apply_overlay_to_image(base_bytes, overlay)

        assert result.size == (500, 750)

    def test_same_size_overlay_not_resized(self):
        composer = ImageComposer()

        base_image = Image.new("RGBA", (2000, 3000), (255, 0, 0, 255))
        overlay = Image.new("RGBA", (2000, 3000), (0, 0, 0, 128))

        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        base_bytes = buffer.getvalue()

        result = composer.apply_overlay_to_image(base_bytes, overlay)

        assert result.size == (2000, 3000)

class TestImageComposerAspectNormalisation:

    def _result_size(self, base_size):
        composer = ImageComposer()
        base = Image.new("RGBA", base_size, (255, 0, 0, 255))
        buf = BytesIO(); base.save(buf, format="PNG")
        overlay = Image.new("RGBA", (10, 10), (0, 0, 0, 128))
        return composer.apply_overlay_to_image(buf.getvalue(), overlay).size

    def test_two_three_source_unchanged(self):
        assert self._result_size((2000, 3000)) == (2000, 3000)
        assert self._result_size((1000, 1500)) == (1000, 1500)

    def test_too_wide_source_cropped_on_sides(self):
        w, h = self._result_size((600, 800))
        assert (w, h) == (533, 800)
        assert abs(w / h - 2 / 3) < 0.01

    def test_too_tall_source_cropped_on_top_bottom(self):
        w, h = self._result_size((1000, 2000))
        assert (w, h) == (1000, 1500)
        assert abs(w / h - 2 / 3) < 0.01

class TestImageComposerInputTypes:

    def test_accepts_bytes(self):
        composer = ImageComposer()

        base_image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 128))

        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        base_bytes = buffer.getvalue()

        result = composer.apply_overlay_to_image(base_bytes, overlay)

        assert isinstance(result, Image.Image)

    def test_accepts_file_path(self, tmp_path):
        composer = ImageComposer()

        base_image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        image_path = tmp_path / "test_image.png"
        base_image.save(image_path, format="PNG")

        overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 128))

        result = composer.apply_overlay_to_image(str(image_path), overlay)

        assert isinstance(result, Image.Image)

    @patch('affiche.app.image.image_composer.requests.get')
    def test_accepts_url(self, mock_get):
        composer = ImageComposer()

        base_image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        buffer.seek(0)

        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [buffer.getvalue()]
        mock_get.return_value = mock_response

        overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 128))

        result = composer.apply_overlay_to_image(
            "https://example.com/poster.jpg",
            overlay
        )

        assert isinstance(result, Image.Image)
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs.get("timeout") == HTTP_TIMEOUT

    @patch('affiche.app.image.image_composer.requests.get')
    def test_url_download_size_cap(self, mock_get):
        composer = ImageComposer()

        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b"x" * (MAX_POSTER_DOWNLOAD_BYTES + 1)]
        mock_get.return_value = mock_response

        overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 128))

        with pytest.raises(ValueError):
            composer.apply_overlay_to_image("https://example.com/huge.jpg", overlay)

    def test_rejects_invalid_input(self):
        composer = ImageComposer()
        overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 128))

        with pytest.raises(ValueError, match="must be URL, filepath, or bytes"):
            composer.apply_overlay_to_image(12345, overlay)

        with pytest.raises(ValueError, match="must be URL, filepath, or bytes"):
            composer.apply_overlay_to_image(None, overlay)

class TestImageComposerColorMode:

    def test_converts_rgb_to_rgba(self):
        composer = ImageComposer()

        base_image = Image.new("RGB", (100, 100), (255, 0, 0))
        overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 128))

        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        base_bytes = buffer.getvalue()

        result = composer.apply_overlay_to_image(base_bytes, overlay)

        assert result.mode == "RGBA"

    def test_converts_l_to_rgba(self):
        composer = ImageComposer()

        base_image = Image.new("L", (100, 100), 128)
        overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 128))

        buffer = BytesIO()
        base_image.save(buffer, format="PNG")
        base_bytes = buffer.getvalue()

        result = composer.apply_overlay_to_image(base_bytes, overlay)

        assert result.mode == "RGBA"
