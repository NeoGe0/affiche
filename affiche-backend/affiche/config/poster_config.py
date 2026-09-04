from affiche.app.image.model import OverlayOptions, TextOptions, GenerationOptions

OVERLAY_OPTIONS = OverlayOptions(border_enabled=True,
                                 border_px=30,
                                 border_color="#000000",
                                 inner_glow_strength=0.0,
                                 inner_glow_color="#000000",
                                 matte_height_ratio=0,
                                 fade_height_ratio=0.5,
                                 gradient_color="#000000")

TEXT_OPTIONS = TextOptions(font_color="#FFFFFF",
                           all_caps=True,
                           min_font_ratio=0.015,
                           max_font_ratio=0.117,
                           max_width_ratio=0.95,
                           max_height_ratio=0.167,
                           text_offset_ratio=0.143,
                           border_padding_ratio=0.015,
                           gravity="south",
                           stroke_enabled=False,
                           break_on_symbols=True,
                           break_symbols=[" - ", ": ", " – "],
                           line_spacing_ratio=0.15,
                           font_name="BebasNeue-Regular.ttf")

GENERATION_OPTIONS = GenerationOptions(jpeg_quality=90)
