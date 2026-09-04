import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Tuple

from affiche.app.image.model import OverlayOptions, TextOptions, GenerationOptions
from affiche.config.env_config import POSTER_CONFIG_FILE
from affiche.config.poster_config import OVERLAY_OPTIONS, TEXT_OPTIONS, GENERATION_OPTIONS

logger = logging.getLogger(__name__)

class PosterConfigStore:
    def __init__(self, path: str = POSTER_CONFIG_FILE):
        self._path = Path(path)

    def get(self) -> Tuple[OverlayOptions, TextOptions, GenerationOptions]:
        if not self._path.exists():
            return OVERLAY_OPTIONS, TEXT_OPTIONS, GENERATION_OPTIONS
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            overlay = OverlayOptions(**data["overlay_options"])
            text = TextOptions(**data["text_options"])
            generation = GenerationOptions.from_dict(data["generation_options"]) if "generation_options" in data else GENERATION_OPTIONS
            return overlay, text, generation
        except (OSError, ValueError, KeyError, TypeError):
            logger.warning("Invalid poster config at %s; using defaults", self._path, exc_info=True)
            return OVERLAY_OPTIONS, TEXT_OPTIONS, GENERATION_OPTIONS

    def save(self, overlay: OverlayOptions, text: TextOptions, generation: GenerationOptions) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "overlay_options": overlay.model_dump(),
                "text_options": text.model_dump(),
                "generation_options": generation.model_dump(),
            },
            indent=2,
        )
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self._path)
        except OSError:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
