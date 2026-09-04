from typing import Optional

MEDIA_FIELDS = (
    "media_resolution",
    "media_width",
    "media_height",
    "video_codec",
    "audio_codec",
    "audio_channels",
    "media_container",
    "media_bitrate",
    "media_size_bytes",
)

def resolution_label(width: Optional[int], height: Optional[int]) -> Optional[str]:
    if not height and not width:
        return None
    h = height or 0
    w = width or 0
    if h >= 4320 or w >= 7680:
        return "8K"
    if h >= 2000 or w >= 3800:
        return "4K"
    if h >= 1400 or w >= 2560:
        return "1440p"
    if h >= 1000 or w >= 1900:
        return "1080p"
    if h >= 700 or w >= 1200:
        return "720p"
    if h >= 550:
        return "576p"
    if h >= 400:
        return "480p"
    return "SD"
