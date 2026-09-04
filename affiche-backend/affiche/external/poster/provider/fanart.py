import logging
from typing import Optional, List

import requests

from affiche.config.http_config import HTTP_TIMEOUT
from affiche.external.poster.provider.base_provider import ExternalProvider

logger = logging.getLogger(__name__)

class FanartClient(ExternalProvider):

    @property
    def name(self) -> str:
        return "fanart"

    def __init__(self, api_key: str, base_url: str = ""):
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")

    def _configure_session(self, session: requests.Session) -> None:
        session.params = {"api_key": self.api_key}

    def get_movie_poster(self,
                         tmdb_id: Optional[int] = None,
                         tvdb_id: Optional[int] = None,
                         language: Optional[str] = None
                         ) -> Optional[str]:
        if not tmdb_id:
            return None
        posters = self._fetch_movie_posters(tmdb_id)
        return posters[0] if posters else None

    def get_show_poster(self,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None
                        ) -> Optional[str]:
        if not tvdb_id:
            return None
        posters = self._fetch_tv_posters(tvdb_id)
        return posters[0] if posters else None

    def get_season_poster(self,
                          season_number: int,
                          tmdb_id: Optional[int] = None,
                          tvdb_id: Optional[int] = None,
                          language: Optional[str] = None
                          ) -> Optional[str]:
        if not tvdb_id:
            return None
        return self._fetch_season_poster(tvdb_id, season_number)

    def get_all_posters(self,
                        media_type: str,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None
                        ) -> List[str]:
        if media_type == "movie":
            if not tmdb_id:
                return []
            return self._fetch_movie_posters(tmdb_id)
        if not tvdb_id:
            return []
        return self._fetch_tv_posters(tvdb_id)

    def get_all_season_posters(self,
                               season_number: int,
                               tmdb_id: Optional[int] = None,
                               tvdb_id: Optional[int] = None,
                               language: Optional[str] = None
                               ) -> List[str]:
        if not tvdb_id:
            return []
        return self._fetch_all_season_poster(tvdb_id, season_number)

    def test_connection(self, api_token) -> bool:
        endpoint = f"{self.base_url}/movies/550"
        session = requests.Session()
        session.params = {"api_key": api_token}
        response = session.get(endpoint, timeout=HTTP_TIMEOUT)
        return response.status_code == 200

    def _fetch_movie_posters(self, tmdb_id: int) -> List[str]:
        try:
            endpoint = f"{self.base_url}/movies/{tmdb_id}"
            response = self.session.get(endpoint, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            poster_urls = []

            movie_posters = data.get("movieposter", [])
            poster_urls.extend([
                poster["url"]
                for poster in movie_posters
                if poster.get("url") and poster.get("lang") == '00'
            ])

            movie_art = data.get("movieart", [])
            poster_urls.extend([
                art["url"]
                for art in movie_art
                if art.get("url")
            ])

            return poster_urls
        except requests.RequestException as e:
            logger.error(f"Error fetching Fanart movie posters for {tmdb_id}: {e}")
            return []

    def _fetch_tv_posters(self, tvdb_id: int) -> List[str]:
        try:
            endpoint = f"{self.base_url}/tv/{tvdb_id}"
            response = self.session.get(endpoint, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            poster_urls = []

            tv_posters = data.get("tvposter", [])
            poster_urls.extend([
                poster["url"]
                for poster in tv_posters
                if poster.get("url")
            ])

            return poster_urls
        except requests.RequestException as e:
            logger.error(f"Error fetching Fanart TV posters for {tvdb_id}: {e}")
            return []

    def _fetch_season_poster(self, tvdb_id: int, season_number: int) -> Optional[str]:
        try:
            endpoint = f"{self.base_url}/tv/{tvdb_id}"
            response = self.session.get(endpoint, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            season_posters = data.get("seasonposter", [])

            for poster in season_posters:
                if poster.get("season") == str(season_number) and poster.get("url"):
                    return poster["url"]

            return None
        except requests.RequestException as e:
            logger.error(f"Error fetching Fanart season poster for {tvdb_id} S{season_number}: {e}")
            return None

    def _fetch_all_season_poster(self, tvdb_id: int, season_number: int) -> List[str]:
        try:
            endpoint = f"{self.base_url}/tv/{tvdb_id}"
            response = self.session.get(endpoint, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            season_posters = data.get("seasonposter", [])
            posters = []
            for poster in season_posters:
                if poster.get("season") == str(season_number) and poster.get("url"):
                    posters.append(poster["url"])

            return posters
        except requests.RequestException as e:
            logger.error(f"Error fetching Fanart season posters for {tvdb_id} S{season_number}: {e}")
            return []
