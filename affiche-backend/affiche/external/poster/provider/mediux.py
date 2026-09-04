import logging
from datetime import datetime
from typing import Optional, List
from urllib.parse import urlparse

import requests

from affiche.config.http_config import HTTP_TIMEOUT
from affiche.external.poster.provider.base_provider import ExternalProvider

logger = logging.getLogger(__name__)

MEDIUX_HOST_SUFFIX = "mediux.io"

_ABSENT_CODE = "FORBIDDEN"

_MOVIE_SETS_QUERY = """
query getMovieSets($tmdb_id: ID!) {
  movies_by_id(id: $tmdb_id) {
    id
    movie_sets {
      popularity
      popularity_global
      movie_poster { id modified_on language { iso_639_1 } }
    }
  }
}
"""

_SHOW_SETS_QUERY = """
query getShowSets($tmdb_id: ID!) {
  shows_by_id(id: $tmdb_id) {
    id
    show_sets {
      popularity
      popularity_global
      show_poster { id modified_on language { iso_639_1 } }
      season_posters {
        id
        modified_on
        language { iso_639_1 }
        season { season_number }
      }
    }
  }
}
"""

_COLLECTION_SETS_QUERY = """
query getCollectionSets($collection_id: ID!) {
  collections_by_id(id: $collection_id) {
    id
    collection_sets {
      popularity
      popularity_global
      collection_poster { id modified_on language { iso_639_1 } }
    }
  }
}
"""

_MOVIE_COLLECTION_QUERY = """
query findMovieCollection($tmdb_id: ID!) {
  movies_by_id(id: $tmdb_id) {
    collection_id { id }
  }
}
"""

_MOVIE_BY_TVDB_QUERY = """
query findMovieByTvdb($tvdb_id: String!) {
  movies(filter: { tvdb_id: { _eq: $tvdb_id } }) { id }
}
"""

_SHOW_BY_TVDB_QUERY = """
query findShowByTvdb($tvdb_id: String!) {
  shows(filter: { tvdb_id: { _eq: $tvdb_id } }) { id }
}
"""

def _normalize_token(token: Optional[str]) -> str:
    token = (token or "").strip()
    if token[:7].lower() == "bearer ":
        token = token[7:].strip()
    return token

def is_mediux_url(url: str) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return host == MEDIUX_HOST_SUFFIX or host.endswith("." + MEDIUX_HOST_SUFFIX)

def mediux_download_headers(url: str, token: Optional[str]) -> dict:
    if not token or not is_mediux_url(url):
        return {}
    return {"Authorization": f"Bearer {token}", "Accept": "image/*"}

class MediuxClient(ExternalProvider):

    supports_collections = True

    @property
    def name(self) -> str:
        return "mediux"

    def __init__(self, api_key: str, base_url: str = ""):
        self.api_key = _normalize_token(api_key)
        self.base_url = (base_url or "").rstrip("/")
        self.graphql_url = f"{self.base_url}/graphql"
        self.image_base = f"{self.base_url}/assets"

    def _configure_session(self, session: requests.Session) -> None:
        session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def get_movie_poster(self,
                         tmdb_id: Optional[int] = None,
                         tvdb_id: Optional[int] = None,
                         language: Optional[str] = None
                         ) -> Optional[str]:
        posters = self.get_all_posters("movie", tmdb_id, tvdb_id, language)
        return posters[0] if posters else None

    def get_show_poster(self,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None
                        ) -> Optional[str]:
        posters = self.get_all_posters("show", tmdb_id, tvdb_id, language)
        return posters[0] if posters else None

    def get_season_poster(self,
                          season_number: int,
                          tmdb_id: Optional[int] = None,
                          tvdb_id: Optional[int] = None,
                          language: Optional[str] = None
                          ) -> Optional[str]:
        posters = self.get_all_season_posters(season_number, tmdb_id, tvdb_id, language)
        return posters[0] if posters else None

    def get_all_posters(self,
                        media_type: str,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None) -> List[str]:
        resolved = self._resolve_tmdb_id(media_type, tmdb_id, tvdb_id)
        if not resolved:
            return []
        sets = self._fetch_sets(media_type, resolved)
        poster_key = "movie_poster" if media_type == "movie" else "show_poster"
        return self._collect_posters(sets, poster_key, language)

    def get_all_season_posters(self,
                               season_number: int,
                               tmdb_id: Optional[int] = None,
                               tvdb_id: Optional[int] = None,
                               language: Optional[str] = None) -> List[str]:
        resolved = self._resolve_tmdb_id("show", tmdb_id, tvdb_id)
        if not resolved:
            return []
        sets = self._fetch_sets("show", resolved)
        return self._collect_season_posters(sets, season_number, language)

    def get_all_collection_posters(self,
                                   collection_id: int,
                                   language: Optional[str] = None) -> List[str]:
        sets = self._fetch_collection_sets(collection_id)
        return self._collect_posters(sets, "collection_poster", language)

    def find_collection_id(self, movie_tmdb_id: int) -> Optional[int]:
        data = self._query(_MOVIE_COLLECTION_QUERY, {"tmdb_id": str(movie_tmdb_id)})
        collection = ((data or {}).get("movies_by_id") or {}).get("collection_id") or {}
        found = collection.get("id")
        try:
            return int(found) if found is not None else None
        except (TypeError, ValueError):
            logger.warning("MediUX answered with a non-numeric collection id: %r", found)
            return None

    def test_connection(self, api_token) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers={"Authorization": f"Bearer {_normalize_token(api_token)}"},
                timeout=5,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _query(self, query: str, variables: dict) -> Optional[dict]:
        try:
            response = self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.error("Error querying MediUX: %s", e)
            return None

        if response.status_code >= 400:
            logger.error("MediUX query failed (HTTP %s): %s",
                         response.status_code, response.text[:500])
            return None
        try:
            payload = response.json()
        except ValueError:
            logger.error("MediUX returned a non-JSON response: %s", response.text[:500])
            return None
        if payload.get("errors"):
            if all((e.get("extensions") or {}).get("code") == _ABSENT_CODE
                   for e in payload["errors"]):
                logger.debug("MediUX does not catalogue %s",
                             [e.get("path") for e in payload["errors"]])
                return payload.get("data") or None
            logger.error("MediUX GraphQL returned errors: %s", payload["errors"])
            return None
        return payload.get("data") or None

    def _resolve_tmdb_id(self,
                         media_type: str,
                         tmdb_id: Optional[int],
                         tvdb_id: Optional[int]) -> Optional[str]:
        if tmdb_id:
            return str(tmdb_id)
        if not tvdb_id:
            return None
        if media_type == "movie":
            query, collection = _MOVIE_BY_TVDB_QUERY, "movies"
        else:
            query, collection = _SHOW_BY_TVDB_QUERY, "shows"
        data = self._query(query, {"tvdb_id": str(tvdb_id)})
        items = (data or {}).get(collection) or []
        return items[0].get("id") if items else None

    def _fetch_sets(self, media_type: str, tmdb_id: str) -> List[dict]:
        if media_type == "movie":
            data = self._query(_MOVIE_SETS_QUERY, {"tmdb_id": tmdb_id})
            node = (data or {}).get("movies_by_id")
            sets = (node or {}).get("movie_sets")
        else:
            data = self._query(_SHOW_SETS_QUERY, {"tmdb_id": tmdb_id})
            node = (data or {}).get("shows_by_id")
            sets = (node or {}).get("show_sets")
        return self._ranked(sets)

    def _fetch_collection_sets(self, collection_id: int) -> List[dict]:
        data = self._query(_COLLECTION_SETS_QUERY, {"collection_id": str(collection_id)})
        node = (data or {}).get("collections_by_id")
        return self._ranked((node or {}).get("collection_sets"))

    @staticmethod
    def _ranked(sets: Optional[List[dict]]) -> List[dict]:
        return sorted(
            sets or [],
            key=lambda s: (s.get("popularity_global") or 0, s.get("popularity") or 0),
            reverse=True,
        )

    def _collect_posters(self, sets: List[dict], poster_key: str,
                         language: Optional[str]) -> List[str]:
        entries = []
        for s in sets:
            for asset in (s.get(poster_key) or []):
                url = self._asset_url(asset)
                if url:
                    entries.append((self._matches_language(asset, language), url))
        return self._ordered_urls(entries, language)

    def _collect_season_posters(self, sets: List[dict], season_number: int,
                                language: Optional[str]) -> List[str]:
        entries = []
        for s in sets:
            for asset in (s.get("season_posters") or []):
                season = asset.get("season") or {}
                if season.get("season_number") != season_number:
                    continue
                url = self._asset_url(asset)
                if url:
                    entries.append((self._matches_language(asset, language), url))
        return self._ordered_urls(entries, language)

    @staticmethod
    def _ordered_urls(entries, language: Optional[str]) -> List[str]:
        if language:
            entries = sorted(entries, key=lambda e: not e[0])
        return [url for _, url in entries]

    @staticmethod
    def _matches_language(asset: dict, language: Optional[str]) -> bool:
        if not language:
            return False
        return ((asset.get("language") or {}).get("iso_639_1")) == language

    def _asset_url(self, asset: dict) -> Optional[str]:
        asset_id = (asset or {}).get("id")
        if not asset_id:
            return None
        url = f"{self.image_base}/{asset_id}"
        version = self._format_modified(asset.get("modified_on"))
        return f"{url}?v={version}" if version else url

    @staticmethod
    def _format_modified(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y%m%d%H%M%S")
        except (ValueError, AttributeError):
            return None
