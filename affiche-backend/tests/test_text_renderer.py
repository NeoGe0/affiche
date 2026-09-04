import pytest
from pathlib import Path
from PIL import Image

from affiche.app.image.model.text_options import TextOptions
from affiche.app.image.font_store import FontStore
from affiche.app.image.text_renderer import TextRenderer, RESOURCES_DIR

class TestTextRendererLineBreaks:

    def setup_method(self):
        self.renderer = TextRenderer()

    def test_apply_line_breaks_with_colon(self):
        options = TextOptions(break_on_symbols=True, break_symbols=[": "])
        result = self.renderer._apply_line_breaks("The Matrix: Reloaded", options)

        assert result == "The Matrix\nReloaded"

    def test_apply_line_breaks_with_dash(self):
        options = TextOptions(break_on_symbols=True, break_symbols=[" - "])
        result = self.renderer._apply_line_breaks("Avengers - Endgame", options)

        assert result == "Avengers\nEndgame"

    def test_apply_line_breaks_disabled(self):
        options = TextOptions(break_on_symbols=False)
        result = self.renderer._apply_line_breaks("The Matrix: Reloaded", options)

        assert result == "The Matrix: Reloaded"

    def test_apply_line_breaks_no_match(self):
        options = TextOptions(break_on_symbols=True, break_symbols=[": "])
        result = self.renderer._apply_line_breaks("Inception", options)

        assert result == "Inception"

class TestTextRendererWordWrap:

    def setup_method(self):
        self.renderer = TextRenderer()

    def test_generate_word_wrap_variants_single_word(self):
        variants = self.renderer._generate_word_wrap_variants("Inception")

        assert variants == ["Inception"]

    def test_generate_word_wrap_variants_two_words(self):
        variants = self.renderer._generate_word_wrap_variants("The Matrix")

        assert "The Matrix" in variants
        assert "The\nMatrix" in variants

    def test_generate_word_wrap_variants_three_words(self):
        variants = self.renderer._generate_word_wrap_variants("The Dark Knight")

        assert "The Dark Knight" in variants
        assert "The\nDark Knight" in variants
        assert "The Dark\nKnight" in variants
        assert "The\nDark\nKnight" in variants

    def test_generate_word_wrap_already_wrapped(self):
        variants = self.renderer._generate_word_wrap_variants("Line One\nLine Two")

        assert variants == ["Line One\nLine Two"]

    def test_find_best_wrap_picks_largest_font(self):
        options = TextOptions(
            max_width_ratio=0.25,
            max_height_ratio=0.167,
            min_font_ratio=0.003,
            max_font_ratio=0.067,
        )

        result = self.renderer._find_best_wrap(
            "LONG TITLE HERE",
            options,
            (2000, 3000)
        )

        assert "\n" in result

class TestTextRendererFontSize:

    def setup_method(self):
        self.renderer = TextRenderer()

    def test_find_optimal_font_size_short_text(self):
        options = TextOptions(
            max_width_ratio=0.95,
            max_height_ratio=0.167,
            min_font_ratio=0.015,
            max_font_ratio=0.1,
        )

        font_size = self.renderer._find_optimal_font_size(
            "HI",
            options,
            (2000, 3000)
        )

        assert font_size >= 200

    def test_find_optimal_font_size_long_text(self):
        options = TextOptions(
            max_width_ratio=0.95,
            max_height_ratio=0.167,
            min_font_ratio=0.015,
            max_font_ratio=0.1,
        )

        font_size = self.renderer._find_optimal_font_size(
            "THE SHAWSHANK REDEMPTION EXTENDED EDITION",
            options,
            (2000, 3000)
        )

        assert font_size < 200

    def test_find_optimal_font_size_respects_image_bounds(self):
        options = TextOptions(
            max_width_ratio=0.95,
            max_height_ratio=0.167,
            min_font_ratio=0.015,
            max_font_ratio=0.1,
            border_padding_ratio=0.015,
        )

        large_img_size = self.renderer._find_optimal_font_size(
            "TEST",
            options,
            (2000, 3000)
        )

        small_img_size = self.renderer._find_optimal_font_size(
            "TEST",
            options,
            (1000, 1500)
        )

        assert small_img_size <= large_img_size

    def test_find_optimal_font_size_shrinks_below_min_to_avoid_overflow(self):
        options = TextOptions(
            max_width_ratio=0.9,
            max_height_ratio=0.5,
            min_font_ratio=0.15,
            max_font_ratio=0.3,
            border_padding_ratio=0.02,
            stroke_enabled=False,
            break_on_symbols=False,
            auto_wrap=False,
        )
        img_w, img_h = 1000, 1500
        text = "PARANORMAL ACTIVITY"

        size = self.renderer._find_optimal_font_size(text, options, (img_w, img_h))

        padding = int(min(img_w, img_h) * options.border_padding_ratio)
        effective_max_width = min(int(img_w * options.max_width_ratio), img_w - 2 * padding)

        assert self.renderer._text_fits(text, size, options, effective_max_width, 10 ** 9)
        assert size < int(img_h * options.min_font_ratio)

    def test_find_optimal_font_size_accounts_for_stroke(self):
        base = dict(max_width_ratio=0.9, max_height_ratio=0.5, min_font_ratio=0.01,
                    max_font_ratio=0.3, border_padding_ratio=0.02, break_on_symbols=False, auto_wrap=False)
        no_stroke = TextOptions(stroke_enabled=False, **base)
        with_stroke = TextOptions(stroke_enabled=True, stroke_width_ratio=0.06, **base)

        text = "PARANORMAL ACTIVITY"
        size_no_stroke = self.renderer._find_optimal_font_size(text, no_stroke, (1000, 1500))
        size_with_stroke = self.renderer._find_optimal_font_size(text, with_stroke, (1000, 1500))

        assert size_with_stroke <= size_no_stroke

class TestTextRendererPosition:

    def setup_method(self):
        self.renderer = TextRenderer()

    def test_position_south_gravity(self):
        options = TextOptions(
            gravity="south",
            text_offset_ratio=100/3000,
            border_padding_ratio=30/2000,
        )

        x, y = self.renderer._calculate_text_position(
            image_size=(2000, 3000),
            text_size=(500, 100),
            options=options
        )

        expected_y = 3000 - 30 - 100 - 100
        assert y == expected_y

    def test_position_north_gravity(self):
        options = TextOptions(
            gravity="north",
            text_offset_ratio=100/3000,
            border_padding_ratio=30/2000,
        )

        x, y = self.renderer._calculate_text_position(
            image_size=(2000, 3000),
            text_size=(500, 100),
            options=options
        )

        assert y == 130

    def test_position_center_gravity(self):
        options = TextOptions(
            gravity="center",
            border_padding_ratio=0,
        )

        x, y = self.renderer._calculate_text_position(
            image_size=(2000, 3000),
            text_size=(500, 100),
            options=options
        )

        assert y == 1450

    def test_position_horizontal_centering(self):
        options = TextOptions(
            gravity="south",
            border_padding_ratio=0,
        )

        x, y = self.renderer._calculate_text_position(
            image_size=(2000, 3000),
            text_size=(500, 100),
            options=options
        )

        assert x == 750

    def test_position_with_border_padding(self):
        options = TextOptions(
            gravity="south",
            border_padding_ratio=100/2000,
        )

        x, y = self.renderer._calculate_text_position(
            image_size=(2000, 3000),
            text_size=(500, 100),
            options=options
        )

        assert x == 750

class TestTextRendererRender:

    def setup_method(self):
        self.renderer = TextRenderer()

    def test_render_text_returns_image(self):
        image = Image.new("RGBA", (2000, 3000), (0, 0, 0, 255))
        options = TextOptions()

        result = self.renderer.render_text(image, "Test", options)

        assert isinstance(result, Image.Image)
        assert result.size == (2000, 3000)

    def test_render_empty_text_returns_original(self):
        image = Image.new("RGBA", (2000, 3000), (0, 0, 0, 255))
        options = TextOptions()

        result = self.renderer.render_text(image, "", options)

        assert result.size == image.size

    def test_render_whitespace_text_returns_original(self):
        image = Image.new("RGBA", (2000, 3000), (0, 0, 0, 255))
        options = TextOptions()

        result = self.renderer.render_text(image, "   ", options)

        assert result.size == image.size

    def test_render_all_caps(self):
        image = Image.new("RGBA", (2000, 3000), (0, 0, 0, 255))
        options = TextOptions(all_caps=True)

        result = self.renderer.render_text(image, "lowercase", options)

        assert isinstance(result, Image.Image)

    def test_render_with_auto_wrap(self):
        image = Image.new("RGBA", (2000, 3000), (0, 0, 0, 255))
        options = TextOptions(
            auto_wrap=True,
            auto_wrap_threshold_ratio=0.067,
            max_width_ratio=0.4,
        )

        result = self.renderer.render_text(
            image,
            "The Lord of the Rings Fellowship",
            options
        )

        assert isinstance(result, Image.Image)

class TestTextRendererBlankLines:

    def setup_method(self):
        self.renderer = TextRenderer()

    def _height(self, text: str, size: int = 100) -> int:
        font = self.renderer._load_font(TextOptions().font_name, size)
        return self.renderer._get_text_bbox(text, font, 0, size)[1]

    def test_blank_line_adds_height(self):
        assert self._height("ONE\n\nTWO") > self._height("ONE\nTWO")

    def test_blank_line_height_scales_with_font_size(self):
        assert self._height("A\n\nB", 200) - self._height("A\nB", 200) == 100

    def test_manual_line_breaks_are_kept(self):
        assert self.renderer._generate_word_wrap_variants("THE\n\nMATRIX") == ["THE\n\nMATRIX"]

class TestTextRendererFonts:

    def setup_method(self):
        self.renderer = TextRenderer()

    def test_list_available_fonts(self):
        fonts = FontStore().list_fonts()

        assert isinstance(fonts, list)
        assert len(fonts) > 0

    def test_load_font_caching(self):
        font1 = self.renderer._load_font("BebasNeue-Regular.ttf", 100)
        font2 = self.renderer._load_font("BebasNeue-Regular.ttf", 100)

        assert font1 is font2

    def test_load_font_different_sizes_not_cached(self):
        font1 = self.renderer._load_font("BebasNeue-Regular.ttf", 100)
        font2 = self.renderer._load_font("BebasNeue-Regular.ttf", 200)

        assert font1 is not font2
