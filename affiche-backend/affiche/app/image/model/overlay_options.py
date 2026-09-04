from dataclasses import dataclass, field, asdict
from typing import Literal
import json

def validate_hex_color(color: str) -> str:

    if not color.startswith("#"):
        raise ValueError(f"Color must start with #: {color}")
    hex_part = color.lstrip("#")
    if len(hex_part) not in [3, 6]:
        raise ValueError(f"Color must be in format #RGB or #RRGGBB: {color}")
    try:
        int(hex_part, 16)
    except ValueError:
        raise ValueError(f"Color must contain valid hex characters: {color}")
    if len(hex_part) == 3:
        return f"#{hex_part[0] * 2}{hex_part[1] * 2}{hex_part[2] * 2}".upper()
    return color.upper()

def validate_range(value: float, min_val: float, max_val: float, name: str) -> float:

    if not min_val <= value <= max_val:
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")
    return value

@dataclass
class OverlayOptions:

    overlay_type: Literal["poster", "background"] = "poster"

    border_enabled: bool = False
    border_px: int = 0
    border_color: str = "#FFFFFF"
    corner_radius: float = 0.0

    matte_height_ratio: float = 0.0
    fade_height_ratio: float = 0.0
    gradient_color: str = "#000000"

    vignette_strength: float = 0.0
    vignette_color: str = "#000000"

    inner_glow_strength: float = 0.0
    inner_glow_color: str = "#000000"

    grain_amount: float = 0.0
    grain_size: float = 1.0

    blur_amount: float = 0.0

    show_text_area: bool = False
    text_box_w: int = 0
    text_box_h: int = 0
    text_box_offset: int = 0

    def __post_init__(self):

        if self.overlay_type not in ("poster", "background"):
            raise ValueError(f"overlay_type must be 'poster' or 'background', got {self.overlay_type}")

        self.border_color = validate_hex_color(self.border_color)
        self.gradient_color = validate_hex_color(self.gradient_color)
        self.vignette_color = validate_hex_color(self.vignette_color)
        self.inner_glow_color = validate_hex_color(self.inner_glow_color)

        validate_range(self.border_px, 0, 500, "border_px")
        validate_range(self.corner_radius, 0.0, 1.0, "corner_radius")
        validate_range(self.matte_height_ratio, 0.0, 1.0, "matte_height_ratio")
        validate_range(self.fade_height_ratio, 0.0, 1.0, "fade_height_ratio")
        validate_range(self.vignette_strength, 0.0, 1.0, "vignette_strength")
        validate_range(self.inner_glow_strength, 0.0, 1.0, "inner_glow_strength")
        validate_range(self.grain_amount, 0.0, 1.0, "grain_amount")
        validate_range(self.grain_size, 0.1, 10.0, "grain_size")
        validate_range(self.blur_amount, 0.0, 100.0, "blur_amount")

        if self.text_box_w < 0:
            raise ValueError(f"text_box_w must be >= 0, got {self.text_box_w}")
        if self.text_box_h < 0:
            raise ValueError(f"text_box_h must be >= 0, got {self.text_box_h}")
        if self.text_box_offset < 0:
            raise ValueError(f"text_box_offset must be >= 0, got {self.text_box_offset}")

    def model_dump(self) -> dict:

        return asdict(self)

    def model_dump_json(self) -> str:

        return json.dumps(asdict(self))

    @classmethod
    def model_validate_json(cls, json_str: str) -> 'OverlayOptions':

        data = json.loads(json_str)
        return cls(**data)
