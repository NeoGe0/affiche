import logging
import threading
from typing import Optional, List

import requests
from tvdb_v4_official import TVDB

from affiche.external.poster.provider.base_provider import BaseUrlMode, ExternalProvider

logger = logging.getLogger(__name__)

LOGIN_URL = "https://api4.thetvdb.com/v4/login"

LANG_2_TO_3 = {
    "en": "eng", "fr": "fra", "de": "deu", "es": "spa", "it": "ita",
    "pt": "por", "nl": "nld", "ja": "jpn", "ko": "kor", "zh": "zho",
}

class TVDBClient(ExternalProvider):

    base_url_mode = BaseUrlMode.NONE

    @property
    def name(self) -> str:
        return "tvdb"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._tvdb = None
        self._tvdb_lock = threading.Lock()

    @property
    def tvdb(self) -> TVDB:
        if self._tvdb is None:
            with self._tvdb_lock:
                if self._tvdb is None:
                    self._tvdb = TVDB(self.api_key)
        return self._tvdb

    def get_movie_poster(self,
                         tmdb_id: Optional[int] = None,
                         tvdb_id: Optional[int] = None,
                         language: Optional[str] = None
                         ) -> Optional[str]:
        if not tvdb_id:
            return None
        posters = self._fetch_all_movie_posters(tvdb_id)
        return posters[0] if posters else None

    def get_show_poster(self,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None
                        ) -> Optional[str]:
        if not tvdb_id:
            return None
        posters = self._fetch_all_series_posters(tvdb_id, language)
        return posters[0] if posters else None

    def get_season_poster(self,
                          season_number: int,
                          tmdb_id: Optional[int] = None,
                          tvdb_id: Optional[int] = None,
                          language: Optional[str] = None
                          ) -> Optional[str]:
        if not tvdb_id:
            return None
        return self._fetch_season_poster(tvdb_id, season_number, language)

    def get_all_posters(self,
                        media_type: str,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None) -> List[str]:
        if not tvdb_id:
            return []
        if media_type == "movie":
            return self._fetch_all_movie_posters(tvdb_id)
        return self._fetch_all_series_posters(tvdb_id, language)

    def get_all_season_posters(self,
                               season_number: int,
                               tmdb_id: Optional[int] = None,
                               tvdb_id: Optional[int] = None,
                               language: Optional[str] = None) -> List[str]:
        if not tvdb_id:
            return []
        return self._fetch_all_season_posters(tvdb_id, season_number)

    def search_by_title(
            self,
            title: str,
            media_type: str,
            year: Optional[int] = None,
    ) -> Optional[str]:
        try:

            results = self.tvdb.search(title, type=self._get_provider_media_type(media_type), year=year)
            if results and len(results) > 0:
                return str(results[0].get("tvdb_id"))
            return None
        except Exception as e:
            logger.error(f"Error searching TVDB for '{title}': {e}")
            return None

    def get_translated_title(
            self,
            media_type: str,
            language: str,
            tmdb_id: Optional[int] = None,
            tvdb_id: Optional[int] = None,
            season_number: Optional[int] = None,
    ) -> Optional[str]:
        if not tvdb_id or season_number is not None:
            return None
        lang = LANG_2_TO_3.get(language)
        if not lang:
            return None
        try:
            if self._get_provider_media_type(media_type) == "movie":
                translation = self.tvdb.get_movie_translation(tvdb_id, lang)
            else:
                translation = self.tvdb.get_series_translation(tvdb_id, lang)
            return (translation or {}).get("name") or None
        except Exception as e:
            logger.error(f"Error fetching TVDB translated title for {tvdb_id} ({lang}): {e}")
            return None

    def test_connection(self, api_token) -> bool:
        try:
            response = requests.post(
                LOGIN_URL,
                json={"apikey": api_token},
                timeout=5,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _fetch_season_poster(
            self,
            tvdb_id: int,
            season_number: int,
            language: Optional[str] = None
    ) -> Optional[str]:
        posters = self._fetch_all_season_posters(tvdb_id, season_number)
        return posters[0] if posters else None

    def _fetch_all_movie_posters(self, tvdb_id: int) -> List[str]:
        try:
            movie_extended = self.tvdb.get_movie_extended(tvdb_id)
            all_artworks: List[dict] = movie_extended.get("artworks", [])
            artworks = [a for a in all_artworks if a.get("type") == 14]
            artworks.sort(key=lambda x: (x.get("language") is not None, -x.get("score", 0)))

            poster_urls = [
                {"url": artwork["image"], "score": artwork.get("score", 0)}
                for artwork in artworks
                if artwork.get("image")
            ]
            poster_urls.sort(key=lambda x: x["score"], reverse=True)

            return [p["url"] for p in poster_urls]
        except Exception as e:
            logger.error(f"Error fetching TVDB movie posters for {tvdb_id}: {e}")
            return []

    def _fetch_all_series_posters(
            self,
            tvdb_id: int,
            language: Optional[str] = None
    ) -> List[str]:
        try:
            artworks = self.tvdb.get_series_artworks(id=tvdb_id, type=2, lang=language)
            if not artworks:
                return []

            poster_urls = [
                {"url": artwork["image"], "score": artwork.get("score", 0)}
                for artwork in artworks.get('artworks', [])
                if artwork.get("image")
            ]
            poster_urls.sort(key=lambda x: x["score"], reverse=True)

            return [p["url"] for p in poster_urls]
        except Exception as e:
            logger.error(f"Error fetching TVDB series posters for {tvdb_id}: {e}")
            return []

    def _fetch_all_season_posters(
            self,
            tvdb_id: int,
            season_number: int
    ) -> List[str]:
        try:
            extended_info = self.tvdb.get_series_extended(tvdb_id)
            seasons = extended_info.get("seasons", [])
            season = next(
                (s for s in seasons if s.get("number") == season_number),
                None
            )
            if not season:
                return []

            season_extended = self.tvdb.get_season_extended(season.get("id"))
            all_artworks = season_extended.get("artwork", [])
            artworks = [a for a in all_artworks if a.get("type") == 14]
            if not artworks:
                return []

            poster_urls = [
                {"url": artwork["image"], "score": artwork.get("score", 0)}
                for artwork in artworks
                if artwork.get("image")
            ]
            poster_urls.sort(key=lambda x: x["score"], reverse=True)

            return [p["url"] for p in poster_urls]
        except Exception as e:
            logger.error(f"Error fetching TVDB season posters for {tvdb_id} S{season_number}: {e}")
            return []

    def _get_provider_media_type(self, media_type: str) -> str:
        return "movie" if media_type == "movie" else "series"
