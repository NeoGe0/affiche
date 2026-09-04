import logging
import threading
import time
from typing import Optional, List

import requests

from affiche.config.http_config import HTTP_TIMEOUT
from affiche.external.poster.provider.base_provider import ExternalProvider

logger = logging.getLogger(__name__)

class TVmazeClient(ExternalProvider):

    requires_api_key = False

    _MIN_REQUEST_INTERVAL = 0.5

    MIN_POSTER_WIDTH = 500

    @property
    def name(self) -> str:
        return "tvmaze"

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self._show_id_cache: dict[int, Optional[int]] = {}
        self._throttle_lock = threading.Lock()
        self._last_request_at = 0.0

    def get_movie_poster(self,
                         tmdb_id: Optional[int] = None,
                         tvdb_id: Optional[int] = None,
                         language: Optional[str] = None
                         ) -> Optional[str]:
        return None

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
        posters = self.get_all_season_posters(season_number, tmdb_id=tmdb_id, tvdb_id=tvdb_id,
                                              language=language)
        return posters[0] if posters else None

    def get_all_posters(self,
                        media_type: str,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None
                        ) -> List[str]:
        if media_type == "movie" or not tvdb_id:
            return []

        show_id = self._resolve_show_id(tvdb_id)
        if show_id is None:
            return []

        images = self._get(f"/shows/{show_id}/images")
        return self._poster_urls(images)

    def get_all_season_posters(self,
                               season_number: int,
                               tmdb_id: Optional[int] = None,
                               tvdb_id: Optional[int] = None,
                               language: Optional[str] = None
                               ) -> List[str]:
        if not tvdb_id:
            return []

        show_id = self._resolve_show_id(tvdb_id)
        if show_id is None:
            return []

        seasons = self._get(f"/shows/{show_id}/seasons")
        if not isinstance(seasons, list):
            return []

        for season in seasons:
            if season.get("number") != season_number:
                continue
            url = ((season.get("image") or {}).get("original")
                   or (season.get("image") or {}).get("medium"))
            return [url] if url else []
        return []

    def test_connection(self, api_token) -> bool:
        response = self.session.get(f"{self.base_url}/shows/1", timeout=HTTP_TIMEOUT)
        return response.status_code == 200

    def _resolve_show_id(self, tvdb_id: int) -> Optional[int]:
        if tvdb_id in self._show_id_cache:
            return self._show_id_cache[tvdb_id]

        show = self._get("/lookup/shows", params={"thetvdb": tvdb_id})
        show_id = show.get("id") if isinstance(show, dict) else None
        self._show_id_cache[tvdb_id] = show_id
        return show_id

    def _poster_urls(self, images) -> List[str]:
        if not isinstance(images, list):
            return []

        candidates = []
        for image in images:
            if not isinstance(image, dict) or image.get("type") != "poster":
                continue
            resolutions = image.get("resolutions") or {}
            original = resolutions.get("original") or resolutions.get("medium") or {}
            url = original.get("url")
            if not url:
                continue
            width = original.get("width") or 0
            if width and width < self.MIN_POSTER_WIDTH:
                continue
            candidates.append((width, url))

        candidates.sort(key=lambda candidate: candidate[0], reverse=True)
        return [url for _, url in candidates]

    def _get(self, path: str, params: Optional[dict] = None):
        self._await_rate_limit()
        try:
            response = self.session.get(f"{self.base_url}{path}", params=params,
                                        timeout=HTTP_TIMEOUT)
            if response.status_code == 404:
                return None
            if response.status_code == 429:
                logger.warning("TVmaze rate limit hit on %s; skipping", path)
                return None
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Error fetching TVmaze {path}: {e}")
            return None

    def _await_rate_limit(self) -> None:
        with self._throttle_lock:
            wait = self._last_request_at + self._MIN_REQUEST_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()
