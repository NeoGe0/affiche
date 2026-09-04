from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class OverlayOptionsResponse(BaseModel):
    overlay_type: Literal["poster", "background"]
    border_enabled: bool
    border_px: int
    border_color: str
    corner_radius: float
    matte_height_ratio: float
    fade_height_ratio: float
    gradient_color: str
    vignette_strength: float
    vignette_color: str
    inner_glow_strength: float
    inner_glow_color: str
    grain_amount: float
    grain_size: float
    blur_amount: float
    show_text_area: bool
    text_box_w: int
    text_box_h: int
    text_box_offset: int

class TextOptionsResponse(BaseModel):
    enabled: bool = True
    font_name: str
    font_color: str
    all_caps: bool
    min_font_ratio: float
    max_font_ratio: float
    max_width_ratio: float
    max_height_ratio: float
    text_offset_ratio: float
    border_padding_ratio: float
    gravity: Literal["south", "north", "center"]
    stroke_enabled: bool
    stroke_color: str
    stroke_width_ratio: float
    line_spacing_ratio: float
    break_on_symbols: bool
    break_symbols: List[str]
    auto_wrap: bool
    auto_wrap_threshold_ratio: float

class GenerationOptionsResponse(BaseModel):
    jpeg_quality: int

class PosterConfigResponse(BaseModel):
    overlay_options: OverlayOptionsResponse
    text_options: TextOptionsResponse
    generation_options: GenerationOptionsResponse

class PosterConfigUpdate(BaseModel):
    overlay_options: OverlayOptionsResponse
    text_options: TextOptionsResponse
    generation_options: GenerationOptionsResponse

class AppSettingsResponse(BaseModel):
    new_library_enabled: bool
    new_library_upload_enabled: bool
    new_library_provider_order: List[str]
    log_level: str
    trash_retention_days: int

class AppSettingsUpdate(BaseModel):
    new_library_enabled: Optional[bool] = None
    new_library_upload_enabled: Optional[bool] = None
    new_library_provider_order: Optional[List[str]] = None
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR"]] = None
    trash_retention_days: Optional[int] = Field(default=None, ge=0)

class AppSettingsInfo(BaseModel):
    version: str
    encryption_key_secure: bool
    database: str
