from dataclasses import dataclass, field, asdict
from typing import Literal, List, Optional
import json

DEFAULT_FONT = "Quintessential-Regular.ttf"

REFERENCE_WIDTH = 2000
REFERENCE_HEIGHT = 3000

@dataclass
class TextOptions:

    enabled: bool = True

    font_name: str = DEFAULT_FONT
    font_color: str = "#FFFFFF"
    all_caps: bool = True

    min_font_ratio: float = 0.015
    max_font_ratio: float = 0.1

    max_width_ratio: float = 0.95
    max_height_ratio: float = 0.167

    text_offset_ratio: float = 0.143

    border_padding_ratio: float = 0.0

    gravity: Literal["south", "north", "center"] = "south"

    stroke_enabled: bool = False
    stroke_color: str = "#000000"
    stroke_width_ratio: float = 0.02

    line_spacing_ratio: float = 0.0

    break_on_symbols: bool = True
    break_symbols: List[str] = field(default_factory=lambda: [" - ", ": ", " – "])

    auto_wrap: bool = True
    auto_wrap_threshold_ratio: float = 0.067

    def __post_init__(self):
        for color_field in [self.font_color, self.stroke_color]:
            if not color_field.startswith("#"):
                raise ValueError(f"Color must start with #: {color_field}")

        if not 0 < self.min_font_ratio <= 1:
            raise ValueError(f"min_font_ratio must be in (0, 1], got {self.min_font_ratio}")
        if not self.min_font_ratio <= self.max_font_ratio <= 1:
            raise ValueError(f"max_font_ratio must be >= min_font_ratio and <= 1")
        if not 0 < self.max_width_ratio <= 1:
            raise ValueError(f"max_width_ratio must be in (0, 1], got {self.max_width_ratio}")
        if not 0 < self.max_height_ratio <= 1:
            raise ValueError(f"max_height_ratio must be in (0, 1], got {self.max_height_ratio}")
        if self.text_offset_ratio < 0:
            raise ValueError(f"text_offset_ratio must be >= 0, got {self.text_offset_ratio}")
        if self.stroke_width_ratio < 0:
            raise ValueError(f"stroke_width_ratio must be >= 0, got {self.stroke_width_ratio}")

    def model_dump(self) -> dict:
        return asdict(self)

    def model_dump_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def model_validate_json(cls, json_str: str) -> 'TextOptions':
        data = json.loads(json_str)
        return cls(**data)
