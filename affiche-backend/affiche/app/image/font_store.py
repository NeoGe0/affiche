import logging
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from PIL import ImageFont

from affiche.config.env_config import USER_FONTS_DIR

logger = logging.getLogger(__name__)

RESOURCES_DIR = Path(__file__).parent.parent.parent.parent / "resources"

MAX_FONT_BYTES = 10 * 1024 * 1024
ALLOWED_FONT_EXTENSIONS = (".ttf", ".otf")

class FontError(Exception):
    pass

class InvalidFontNameError(FontError):
    pass

class InvalidFontFileError(FontError):
    pass

class FontTooLargeError(FontError):
    pass

class FontNotFoundError(FontError):
    pass

class BundledFontError(FontError):
    pass

class FontStore:

    def __init__(self,
                 bundled_dir: Optional[Path] = None,
                 user_dir: Optional[Path] = None):
        self._bundled_dir = bundled_dir or RESOURCES_DIR
        self._user_dir = user_dir or Path(USER_FONTS_DIR)

        if not self._bundled_dir.exists():
            logger.warning(
                "Bundled fonts directory %s is missing — no fonts will be listed and title "
                "rendering will fail. Check that resources/ ships with the deployment.",
                self._bundled_dir,
            )

    def list_fonts(self) -> List[str]:
        return sorted(set(self._names_in(self._bundled_dir) + self._names_in(self._user_dir)))

    def list_user_fonts(self) -> List[str]:
        return sorted(self._names_in(self._user_dir))

    def read(self, filename: str) -> bytes:
        if filename not in self.list_fonts():
            raise FontNotFoundError("Font not found")

        for directory in (self._bundled_dir, self._user_dir):
            candidate = directory / filename
            if candidate.exists():
                try:
                    return candidate.read_bytes()
                except OSError as e:
                    raise FontNotFoundError("Font not found") from e
        raise FontNotFoundError("Font not found")

    def save(self, filename: str, content: bytes) -> str:
        name = self.safe_name(filename)
        if len(content) > MAX_FONT_BYTES:
            raise FontTooLargeError("Font file too large")
        if not content:
            raise InvalidFontFileError("Empty file")

        try:
            ImageFont.truetype(BytesIO(content), 12)
        except (OSError, IOError, ValueError) as e:
            raise InvalidFontFileError("File is not a valid font") from e

        self._user_dir.mkdir(parents=True, exist_ok=True)
        (self._user_dir / name).write_bytes(content)
        logger.info("Uploaded font %s", name)
        return name

    def delete(self, filename: str) -> None:
        name = self.safe_name(filename)
        user_path = self._user_dir / name

        if not user_path.exists():
            if (self._bundled_dir / name).exists():
                raise BundledFontError("Bundled fonts cannot be deleted")
            raise FontNotFoundError("Font not found")

        user_path.unlink()
        logger.info("Deleted font %s", name)

    @staticmethod
    def safe_name(filename: str) -> str:
        name = Path(filename).name
        if name != filename or not name or name.startswith("."):
            raise InvalidFontNameError("Invalid font filename")
        if not name.lower().endswith(ALLOWED_FONT_EXTENSIONS):
            raise InvalidFontNameError("Font must be a .ttf or .otf file")
        return name

    @staticmethod
    def _names_in(directory: Path) -> List[str]:
        if not directory.exists():
            return []
        return [f.name for f in directory.iterdir()
                if f.is_file() and f.suffix.lower() in ALLOWED_FONT_EXTENSIONS]
