import ipaddress
import logging
import re
import socket
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from PIL import Image

from affiche.config.env_config import CUSTOM_POSTER_DIR

logger = logging.getLogger(__name__)

CUSTOM_SCHEME = "custom:"
MAX_CUSTOM_POSTER_BYTES = 20 * 1024 * 1024
STALE_AGE_SECONDS = 6 * 60 * 60
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")

_FORMAT_MEDIA_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
}

class CustomPosterError(ValueError):
    pass

def _dir() -> Path:
    path = Path(CUSTOM_POSTER_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path

def _validate_is_image(data: bytes) -> None:
    if not data:
        raise CustomPosterError("Empty image")
    try:
        Image.open(BytesIO(data)).verify()
    except Exception:
        raise CustomPosterError("File is not a valid image")

def stage_bytes(data: bytes) -> str:
    if len(data) > MAX_CUSTOM_POSTER_BYTES:
        raise CustomPosterError("Image too large")
    _validate_is_image(data)
    _sweep_stale()
    token = uuid.uuid4().hex
    (_dir() / token).write_bytes(data)
    logger.info("Staged custom poster %s (%d bytes)", token, len(data))
    return token

def staged_path(token: str) -> Optional[Path]:
    if not token or not _TOKEN_RE.match(token):
        return None
    path = _dir() / token
    return path if path.is_file() else None

def media_type_of(path: Path) -> str:
    try:
        with Image.open(path) as img:
            return _FORMAT_MEDIA_TYPES.get(img.format, "application/octet-stream")
    except Exception:
        return "application/octet-stream"

def resolve_source(poster_url: str) -> str:
    if not poster_url or not poster_url.startswith(CUSTOM_SCHEME):
        return poster_url
    token = poster_url[len(CUSTOM_SCHEME):]
    path = staged_path(token)
    if path is None:
        raise CustomPosterError("Custom poster not found or expired")
    return str(path)

def download_user_image(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise CustomPosterError("URL must be http(s)")
    host = parsed.hostname
    if not host:
        raise CustomPosterError("Invalid URL")

    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise CustomPosterError("Could not resolve host")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise CustomPosterError("URL host is not allowed")

    try:
        with requests.get(url, timeout=15, stream=True, allow_redirects=False,
                          headers={"User-Agent": "Mozilla/5.0 (compatible; Affiche/1.0)"}) as resp:
            if resp.is_redirect:
                raise CustomPosterError("Refusing to follow redirect")
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise CustomPosterError("URL did not return an image")
            chunks, total = [], 0
            for chunk in resp.iter_content(8192):
                total += len(chunk)
                if total > MAX_CUSTOM_POSTER_BYTES:
                    raise CustomPosterError("Image too large")
                chunks.append(chunk)
            return b"".join(chunks)
    except requests.RequestException as e:
        raise CustomPosterError(f"Could not download image: {e}")

def _sweep_stale() -> None:
    try:
        now = time.time()
        for entry in _dir().iterdir():
            if entry.is_file() and now - entry.stat().st_mtime > STALE_AGE_SECONDS:
                entry.unlink(missing_ok=True)
    except OSError:
        logger.debug("Custom-poster sweep failed", exc_info=True)
