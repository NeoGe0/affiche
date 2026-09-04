import json

from alembic import op
import sqlalchemy as sa

revision = 'a2c4e6f8b1d3'
down_revision = 'f4b8d2c6a9e1'
branch_labels = None
depends_on = None

SEEDED_OVERLAY_OPTIONS = {
    "overlay_type": "poster",
    "border_enabled": True,
    "border_px": 30,
    "border_color": "#000000",
    "corner_radius": 0.0,
    "matte_height_ratio": 0,
    "fade_height_ratio": 0.5,
    "gradient_color": "#000000",
    "vignette_strength": 0.0,
    "vignette_color": "#000000",
    "inner_glow_strength": 0.0,
    "inner_glow_color": "#000000",
    "grain_amount": 0.0,
    "grain_size": 1.0,
    "blur_amount": 0.0,
    "show_text_area": False,
    "text_box_w": 0,
    "text_box_h": 0,
    "text_box_offset": 0,
}

SEEDED_TEXT_OPTIONS = {
    "enabled": True,
    "font_name": "BebasNeue-Regular.ttf",
    "font_color": "#FFFFFF",
    "all_caps": True,
    "min_font_ratio": 0.015,
    "max_font_ratio": 0.117,
    "max_width_ratio": 0.95,
    "max_height_ratio": 0.167,
    "text_offset_ratio": 0.143,
    "border_padding_ratio": 0.015,
    "gravity": "south",
    "stroke_enabled": False,
    "stroke_color": "#000000",
    "stroke_width_ratio": 0.02,
    "line_spacing_ratio": 0.15,
    "break_on_symbols": True,
    "break_symbols": [" - ", ": ", " – "],
    "auto_wrap": True,
    "auto_wrap_threshold_ratio": 0.067,
}

def _matches_seed(raw, seed: dict) -> bool:
    if raw is None:
        return False
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return False
    return raw == seed

def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT library_id, overlay_options, text_options FROM library_settings"
    )).fetchall()

    for library_id, overlay_options, text_options in rows:
        updates = []
        if _matches_seed(overlay_options, SEEDED_OVERLAY_OPTIONS):
            updates.append("overlay_options = NULL")
        if _matches_seed(text_options, SEEDED_TEXT_OPTIONS):
            updates.append("text_options = NULL")
        if updates:
            connection.execute(
                sa.text(f"UPDATE library_settings SET {', '.join(updates)} WHERE library_id = :id"),
                {"id": library_id},
            )

def downgrade() -> None:
    pass
