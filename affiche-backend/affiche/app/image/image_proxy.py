import logging
from typing import NamedTuple, Optional
from urllib.parse import unquote, urlparse

import requests

from affiche.app.service_configuration.service.service_configuration_service import (
    ServiceConfigurationService,
)
from affiche.external.poster.provider.mediux import is_mediux_url, mediux_download_headers
from affiche.external.poster.provider.shoko import is_shoko_url, shoko_download_headers

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024

REQUEST_TIMEOUT_SECONDS = 15

ALLOWED_IMAGE_HOST_SUFFIXES = ("image.tmdb.org", "thetvdb.com", "fanart.tv", "mediux.io",
                               "tvmaze.com")

ALLOWED_IMAGE_CONTENT_TYPES = (
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/avif",
)

class ImageProxyError(Exception):
    pass

class InvalidImageUrlError(ImageProxyError):
    pass

class ImageHostNotAllowedError(ImageProxyError):
    pass

class UnsupportedImageTypeError(ImageProxyError):
    pass

class ImageTooLargeError(ImageProxyError):
    pass

class ImageFetchError(ImageProxyError):
    pass

class ProxiedImage(NamedTuple):
    content: bytes
    content_type: str

def _media_type(content_type_header: str) -> str:
    return content_type_header.split(";", 1)[0].strip().lower()

def _is_allowed_image_host(host: str) -> bool:
    host = host.lower()
    return any(
        host == suffix or host.endswith("." + suffix)
        for suffix in ALLOWED_IMAGE_HOST_SUFFIXES
    )

class ImageProxyService:

    def __init__(self, config_service: ServiceConfigurationService):
        self._config_service = config_service

    def fetch(self, url: str) -> ProxiedImage:
        decoded_url = unquote(url)
        parsed = urlparse(decoded_url)

        if parsed.scheme not in ("http", "https"):
            raise InvalidImageUrlError("Invalid URL scheme")

        shoko_base_url = None
        if not _is_allowed_image_host(parsed.hostname or ""):
            shoko_base_url = self._shoko_base_url()
            if not is_shoko_url(decoded_url, shoko_base_url):
                raise ImageHostNotAllowedError("Image host not allowed")

        return self._download(decoded_url, self._request_headers(decoded_url, shoko_base_url))

    def _request_headers(self, url: str, shoko_base_url: Optional[str]) -> dict:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Affiche/1.0)"}
        if is_mediux_url(url):
            mediux_config = self._config_service.get_config("mediux")
            token = mediux_config.token if (
                mediux_config and mediux_config.enabled and mediux_config.token) else None
            headers.update(mediux_download_headers(url, token))
        elif shoko_base_url:
            shoko_config = self._config_service.get_config("shoko")
            headers.update(shoko_download_headers(
                url, shoko_base_url, shoko_config.token if shoko_config else None))
        return headers

    def _download(self, url: str, headers: dict) -> ProxiedImage:
        try:
            with requests.get(
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                stream=True,
                allow_redirects=False,
                headers=headers,
            ) as response:
                if response.is_redirect:
                    raise ImageFetchError("Refusing to follow redirect")
                response.raise_for_status()

                content_type = _media_type(response.headers.get("content-type", ""))
                if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                    raise UnsupportedImageTypeError("URL did not return a supported image")

                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > MAX_IMAGE_BYTES:
                            raise ImageTooLargeError("Image too large")
                    except ValueError:
                        pass

                chunks = []
                total = 0
                for chunk in response.iter_content(8192):
                    total += len(chunk)
                    if total > MAX_IMAGE_BYTES:
                        raise ImageTooLargeError("Image too large")
                    chunks.append(chunk)

            return ProxiedImage(content=b"".join(chunks), content_type=content_type)
        except requests.RequestException as e:
            logger.error("Failed to proxy image from %s: %s", url, e)
            raise ImageFetchError("Failed to fetch image") from e

    def _shoko_base_url(self) -> Optional[str]:
        try:
            config = self._config_service.get_config("shoko")
        except Exception:
            logger.warning("Could not read the Shoko configuration; refusing the proxy exception",
                           exc_info=True)
            return None
        if not (config and config.enabled and config.token and config.url):
            return None
        return config.url
