import pytest
from affiche.app.image.model.text_options import TextOptions

class TestTextOptionsValidation:

    def test_default_values(self):
        options = TextOptions()

        assert options.font_color == "#FFFFFF"
        assert options.all_caps is True
        assert options.min_font_ratio == 0.015
        assert options.max_font_ratio == 0.1
        assert options.gravity == "south"
        assert options.auto_wrap is True

    def test_valid_hex_colors(self):
        options = TextOptions(font_color="#FF0000", stroke_color="#00FF00")

        assert options.font_color == "#FF0000"
        assert options.stroke_color == "#00FF00"

    def test_invalid_hex_color_raises(self):
        with pytest.raises(ValueError, match="must start with #"):
            TextOptions(font_color="FF0000")

        with pytest.raises(ValueError, match="must start with #"):
            TextOptions(stroke_color="red")

    def test_min_font_ratio_validation(self):
        with pytest.raises(ValueError, match="min_font_ratio must be in"):
            TextOptions(min_font_ratio=0)

        with pytest.raises(ValueError, match="min_font_ratio must be in"):
            TextOptions(min_font_ratio=1.5)

    def test_max_font_ratio_validation(self):
        with pytest.raises(ValueError, match="max_font_ratio must be >= min_font_ratio"):
            TextOptions(min_font_ratio=0.1, max_font_ratio=0.05)

    def test_max_width_ratio_validation(self):
        with pytest.raises(ValueError, match="max_width_ratio must be in"):
            TextOptions(max_width_ratio=0)

        with pytest.raises(ValueError, match="max_width_ratio must be in"):
            TextOptions(max_width_ratio=1.5)

    def test_max_height_ratio_validation(self):
        with pytest.raises(ValueError, match="max_height_ratio must be in"):
            TextOptions(max_height_ratio=0)

    def test_text_offset_ratio_validation(self):
        with pytest.raises(ValueError, match="text_offset_ratio must be >= 0"):
            TextOptions(text_offset_ratio=-0.1)

    def test_stroke_width_ratio_validation(self):
        with pytest.raises(ValueError, match="stroke_width_ratio must be >= 0"):
            TextOptions(stroke_width_ratio=-0.1)

    def test_model_dump(self):
        options = TextOptions(font_color="#FF0000", max_width_ratio=0.8)
        data = options.model_dump()

        assert isinstance(data, dict)
        assert data["font_color"] == "#FF0000"
        assert data["max_width_ratio"] == 0.8

    def test_model_dump_json_roundtrip(self):
        original = TextOptions(
            font_color="#AABBCC",
            max_width_ratio=0.9,
            auto_wrap=False
        )

        json_str = original.model_dump_json()
        restored = TextOptions.model_validate_json(json_str)

        assert restored.font_color == original.font_color
        assert restored.max_width_ratio == original.max_width_ratio
        assert restored.auto_wrap == original.auto_wrap
