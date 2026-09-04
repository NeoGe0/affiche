import logging
from io import BytesIO

from PIL import Image

logger = logging.getLogger(__name__)

THUMBNAIL_WIDTH = 300
THUMBNAIL_QUALITY = 80

def make_thumbnail(data: bytes, width: int = THUMBNAIL_WIDTH) -> bytes:
    with Image.open(BytesIO(data)) as image:
        thumb = image.convert("RGB")

        if thumb.width > width:
            height = max(1, round(thumb.height * width / thumb.width))
            thumb = thumb.resize((width, height), Image.Resampling.LANCZOS)

        output = BytesIO()
        thumb.save(output, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
        return output.getvalue()
