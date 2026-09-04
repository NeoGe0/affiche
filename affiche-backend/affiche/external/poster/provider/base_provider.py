import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, List

import requests

class BaseUrlMode(str, Enum):
    NONE = "none"
    FIXED = "fixed"
    USER = "user"

class ExternalProvider(ABC):

    requires_api_key: bool = True
    base_url_mode: BaseUrlMode = BaseUrlMode.FIXED

    supports_collections: bool = False

    @classmethod
    def uses_base_url(cls) -> bool:
        return cls.base_url_mode is not BaseUrlMode.NONE

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def supports(self, provider: str) -> bool:
        return self.name == provider

    @property
    def session(self) -> requests.Session:
        override = self.__dict__.get("_session_override")
        if override is not None:
            return override

        local = self.__dict__.get("_local")
        if local is None:
            local = self.__dict__.setdefault("_local", threading.local())

        session = getattr(local, "session", None)
        if session is None:
            session = requests.Session()
            self._configure_session(session)
            local.session = session
        return session

    @session.setter
    def session(self, session: requests.Session) -> None:
        self.__dict__["_session_override"] = session

    def _configure_session(self, session: requests.Session) -> None:
        return None

    @abstractmethod
    def get_movie_poster(
            self,
            tmdb_id: Optional[int] = None,
            tvdb_id: Optional[int] = None,
            language: Optional[str] = None
    ) -> Optional[str]:
        pass

    @abstractmethod
    def get_show_poster(
            self,
            tmdb_id: Optional[int] = None,
            tvdb_id: Optional[int] = None,
            language: Optional[str] = None
    ) -> Optional[str]:
        pass

    @abstractmethod
    def get_season_poster(
            self,
            season_number: int,
            tmdb_id: Optional[int] = None,
            tvdb_id: Optional[int] = None,
            language: Optional[str] = None
    ) -> Optional[str]:
        pass

    @abstractmethod
    def get_all_posters(
            self,
            media_type: str,
            tmdb_id: Optional[int] = None,
            tvdb_id: Optional[int] = None,
            language: Optional[str] = None
    ) -> List[str]:
        pass

    @abstractmethod
    def get_all_season_posters(
            self,
            season_number: int,
            tmdb_id: Optional[int] = None,
            tvdb_id: Optional[int] = None,
            language: Optional[str] = None
    ) -> List[str]:
        pass

    def get_all_collection_posters(
            self,
            collection_id: int,
            language: Optional[str] = None
    ) -> List[str]:
        return []

    def find_collection_id(self, movie_tmdb_id: int) -> Optional[int]:
        return None

    def search_by_title(
            self,
            title: str,
            media_type: str,
            year: Optional[int] = None,
    ) -> Optional[str]:
        return None

    def get_translated_title(
            self,
            media_type: str,
            language: str,
            tmdb_id: Optional[int] = None,
            tvdb_id: Optional[int] = None,
            season_number: Optional[int] = None,
    ) -> Optional[str]:
        return None

    @abstractmethod
    def test_connection(self, api_token) -> bool:
        return False
