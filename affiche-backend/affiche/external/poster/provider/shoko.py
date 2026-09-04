import logging
from typing import Optional, List
from urllib.parse import urlparse

import requests

from affiche.config.http_config import HTTP_TIMEOUT
from affiche.external.poster.provider.base_provider import BaseUrlMode, ExternalProvider

logger = logging.getLogger(__name__)

def is_shoko_url(url: str, configured_base_url: Optional[str]) -> bool:
    if not url or not configured_base_url:
        return False
    target, configured = urlparse(url), urlparse(configured_base_url)
    if not target.hostname or not configured.hostname:
        return False
    return (
        target.scheme == configured.scheme
        and target.hostname.lower() == configured.hostname.lower()
        and target.port == configured.port
    )

def shoko_download_headers(url: str, base_url: Optional[str], token: Optional[str]) -> dict:
    if not token or not is_shoko_url(url, base_url):
        return {}
    return {"apikey": token, "Accept": "image/*"}

class ShokoClient(ExternalProvider):

    base_url_mode = BaseUrlMode.USER
    _EXCLUDED_SOURCES = frozenset({"tmdb"})
    MIN_POSTER_WIDTH = 500

    @property
    def name(self) -> str:
        return "shoko"

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip().rstrip("/")
        self._series_id_cache: dict[tuple[str, int], Optional[int]] = {}

    def _configure_session(self, session: requests.Session) -> None:
        session.headers.update({"apikey": self.api_key})

    def get_movie_poster(self,
                         tmdb_id: Optional[int] = None,
                         tvdb_id: Optional[int] = None,
                         language: Optional[str] = None
                         ) -> Optional[str]:
        posters = self.get_all_posters("movie", tmdb_id=tmdb_id, tvdb_id=tvdb_id, language=language)
        return posters[0] if posters else None

    def get_show_poster(self,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None
                        ) -> Optional[str]:
        posters = self.get_all_posters("show", tmdb_id=tmdb_id, tvdb_id=tvdb_id, language=language)
        return posters[0] if posters else None

    def get_season_poster(self,
                          season_number: int,
                          tmdb_id: Optional[int] = None,
                          tvdb_id: Optional[int] = None,
                          language: Optional[str] = None
                          ) -> Optional[str]:
        return None

    def get_all_posters(self,
                        media_type: str,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None
                        ) -> List[str]:
        if not self.base_url or not tmdb_id:
            return []

        series_id = self._resolve_series_id(media_type, tmdb_id)
        if series_id is None:
            return []

        images = self._get(f"/api/v3/Series/{series_id}/Images")
        return self._poster_urls(images, language)

    def get_all_season_posters(self,
                               season_number: int,
                               tmdb_id: Optional[int] = None,
                               tvdb_id: Optional[int] = None,
                               language: Optional[str] = None
                               ) -> List[str]:
        return []

    def test_connection(self, api_token) -> bool:
        if not self.base_url:
            return False
        response = self.session.get(
            f"{self.base_url}/api/v3/Series",
            params={"pageSize": 1},
            headers={"apikey": (api_token or self.api_key or "").strip()},
            timeout=HTTP_TIMEOUT,
        )
        return response.status_code == 200

    def _resolve_series_id(self, media_type: str, tmdb_id: int) -> Optional[int]:
        key = (media_type, tmdb_id)
        if key in self._series_id_cache:
            return self._series_id_cache[key]

        endpoint = "Movie" if media_type == "movie" else "Show"
        series = self._get(f"/api/v3/Tmdb/{endpoint}/{tmdb_id}/Shoko/Series")

        series_id = None
        if isinstance(series, list):
            for entry in series:
                if not isinstance(entry, dict):
                    continue
                candidate = (entry.get("IDs") or {}).get("ID")
                if isinstance(candidate, int):
                    series_id = candidate
                    break

        self._series_id_cache[key] = series_id
        return series_id

    def _poster_urls(self, images, language: Optional[str]) -> List[str]:
        if not isinstance(images, dict):
            return []

        candidates = []
        for image in images.get("Posters") or []:
            if not isinstance(image, dict):
                continue
            source = str(image.get("Source") or "").lower()
            if source in self._EXCLUDED_SOURCES:
                continue
            if language and not self._matches_language(image, language):
                continue
            url = self._image_url(image)
            if not url:
                continue
            width = image.get("Width") or 0
            if width and width < self.MIN_POSTER_WIDTH:
                continue
            candidates.append((width, url))

        candidates.sort(key=lambda candidate: candidate[0], reverse=True)
        return [url for _, url in candidates]

    @staticmethod
    def _matches_language(image: dict, language: str) -> bool:
        code = image.get("LanguageCode")
        if not code:
            return False
        return str(code).lower() == language.lower()

    def _image_url(self, image: dict) -> Optional[str]:
        identifier = image.get("UID") or image.get("ID")
        if not identifier:
            return None
        return f"{self.base_url}/api/v3/Image/{identifier}"

    def _get(self, path: str, params: Optional[dict] = None):
        try:
            response = self.session.get(f"{self.base_url}{path}", params=params,
                                        timeout=HTTP_TIMEOUT)
            if response.status_code in (401, 403):
                logger.warning("Shoko rejected the configured API key on %s", path)
                return None
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Error fetching Shoko {path}: {e}")
            return None
