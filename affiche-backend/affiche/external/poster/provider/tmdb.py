import logging
from typing import Optional, List

import requests

from affiche.config.http_config import HTTP_TIMEOUT
from affiche.external.poster.provider.base_provider import ExternalProvider

logger = logging.getLogger(__name__)

class TMDBClient(ExternalProvider):

    supports_collections = True
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    @property
    def name(self) -> str:
        return "tmdb"

    def __init__(self, api_key: str, base_url: str = ""):
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")

    def _configure_session(self, session: requests.Session) -> None:
        session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def get_movie_poster(self,
                         tmdb_id: Optional[int] = None,
                         tvdb_id: Optional[int] = None,
                         language: Optional[str] = None
                         ) -> Optional[str]:
        if not tmdb_id:
            return None
        posters = self._fetch_all_posters(tmdb_id, "movie", language)
        return posters[0] if posters else None

    def get_show_poster(self,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None
                        ) -> Optional[str]:
        if not tmdb_id:
            return None
        posters = self._fetch_all_posters(tmdb_id, "tv", language)
        return posters[0] if posters else None

    def get_season_poster(self,
                          season_number: int,
                          tmdb_id: Optional[int] = None,
                          tvdb_id: Optional[int] = None,
                          language: Optional[str] = None
                          ) -> Optional[str]:
        if not tmdb_id:
            return None
        posters = self._fetch_season_posters(tmdb_id, season_number, language)
        return posters[0] if posters else None

    def get_all_posters(self,
                        media_type: str,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None) -> List[str]:
        return self._fetch_all_posters(
            tmdb_id,
            self._get_provider_media_type(media_type),
            language
        )

    def get_all_season_posters(self, season_number: int, tmdb_id: Optional[int] = None, tvdb_id: Optional[int] = None,
                               language: Optional[str] = None) -> List[str]:
        return self._fetch_season_posters(tmdb_id, season_number, language)

    def get_all_collection_posters(self, collection_id: int,
                                   language: Optional[str] = None) -> List[str]:
        return self._fetch_all_posters(collection_id, "collection", language)

    def find_collection_id(self, movie_tmdb_id: int) -> Optional[int]:
        try:
            response = self.session.get(f"{self.base_url}/movie/{movie_tmdb_id}",
                                        timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            collection = response.json().get("belongs_to_collection")
            return collection.get("id") if collection else None
        except requests.RequestException as e:
            logger.error(f"Error resolving the TMDB collection of movie {movie_tmdb_id}: {e}")
            return None

    def search_by_title(
            self,
            title: str,
            media_type: str,
            year: Optional[int] = None,
    ) -> Optional[str]:
        try:
            provider_media_type = self._get_provider_media_type(media_type)
            endpoint = f"{self.base_url}/search/{provider_media_type}"
            params = {"query": title}
            if year:
                params["year" if provider_media_type == "movie" else "first_air_date_year"] = str(year)

            response = self.session.get(endpoint, params=params, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if results:
                return str(results[0]["id"])
            return None
        except requests.RequestException as e:
            logger.error(f"Error searching TMDB for '{title}': {e}")
            return None

    def get_translated_title(
            self,
            media_type: str,
            language: str,
            tmdb_id: Optional[int] = None,
            tvdb_id: Optional[int] = None,
            season_number: Optional[int] = None,
    ) -> Optional[str]:
        if not tmdb_id:
            return None
        try:
            provider_media_type = self._get_provider_media_type(media_type)
            if season_number is not None:
                endpoint = f"{self.base_url}/tv/{tmdb_id}/season/{season_number}"
                field = "name"
            elif provider_media_type == "movie":
                endpoint = f"{self.base_url}/movie/{tmdb_id}"
                field = "title"
            else:
                endpoint = f"{self.base_url}/tv/{tmdb_id}"
                field = "name"

            response = self.session.get(endpoint, params={"language": language}, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            title = response.json().get(field)
            return title or None
        except requests.RequestException as e:
            logger.error(f"Error fetching TMDB translated title for {tmdb_id} ({language}): {e}")
            return None

    def test_connection(self, api_token) -> bool:
        endpoint = f"{self.base_url}/configuration"
        response = self.session.get(
            endpoint,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=5,
        )
        return response.status_code == 200

    def _fetch_all_posters(
            self,
            tmdb_id: int,
            media_type: str,
            language: Optional[str] = None
    ) -> List[str]:
        try:
            lg = language or 'null'
            endpoint = f"{self.base_url}/{media_type}/{tmdb_id}/images?language={lg}"
            response = self.session.get(endpoint, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            posters = data.get("posters", [])
            posters.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

            return [
                f"{self.IMAGE_BASE_URL}{poster['file_path']}"
                for poster in posters
                if poster.get("file_path")
            ]
        except requests.RequestException as e:
            logger.error(f"Error fetching TMDB posters for {tmdb_id}: {e}")
            return []

    def _fetch_season_posters(
            self,
            tmdb_id: int,
            season_number: int,
            language: Optional[str] = None
    ) -> List[str]:
        try:
            lg = language or 'null'
            endpoint = f"{self.base_url}/tv/{tmdb_id}/season/{season_number}/images?language={lg}"
            response = self.session.get(endpoint, timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            posters = data.get("posters", [])
            posters.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

            return [
                f"{self.IMAGE_BASE_URL}{poster['file_path']}"
                for poster in posters
                if poster.get("file_path")
            ]
        except requests.RequestException as e:
            logger.error(f"Error fetching TMDB season posters for {tmdb_id} S{season_number}: {e}")
            return []

    def _get_provider_media_type(self, media_type: str) -> str:
        return "movie" if media_type == "movie" else "tv"
