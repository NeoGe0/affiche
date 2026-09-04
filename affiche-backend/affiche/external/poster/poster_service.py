import logging
from dataclasses import dataclass
from typing import Callable, NamedTuple, Optional, List, TypeVar

from affiche.app.service_configuration.exceptions import NoProvidersConfiguredError
from affiche.external.poster.provider.base_provider import ExternalProvider

logger = logging.getLogger(__name__)

T = TypeVar("T")

@dataclass
class MediaIds:
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None

class ProviderPoster(NamedTuple):
    url: str
    provider: str
    rank: int = 0
    rank_score: float = 1.0

MIN_AGREEING_MEMBERS = 2

class PosterAggregatorService:

    def __init__(
            self,
            providers: List[ExternalProvider]
    ):
        if not providers:
            raise NoProvidersConfiguredError()
        self.providers = providers

    def search_by_title(self,
                        title: str,
                        media_type: str,
                        year: Optional[int] = None,) -> MediaIds:
        ids = MediaIds()

        for provider in self.providers:
            def lookup(p=provider):
                result = p.search_by_title(title, media_type, year)
                return int(result) if result else None

            found = self._ask(provider, lookup, None)
            if found is None:
                continue
            if provider.name == "tmdb":
                ids.tmdb_id = found
            elif provider.name == "tvdb":
                ids.tvdb_id = found

        return ids

    def find_best_poster(self,
                         title: str,
                         tmdb_id: int,
                         tvdb_id: int,
                         media_type: str,
                         provider_order: List[str],
                         language: Optional[str] = None,
                         ) -> Optional[ProviderPoster]:

        for provider in self._get_providers_by_order(provider_order):
            def lookup(p=provider):
                if media_type == "movie":
                    return p.get_movie_poster(tmdb_id=tmdb_id, tvdb_id=tvdb_id, language=language)
                return p.get_show_poster(tmdb_id=tmdb_id, tvdb_id=tvdb_id, language=language)

            result = self._ask(provider, lookup, None)
            if result:
                return ProviderPoster(result, provider.name)

        logger.warning(f"Could not find any poster for {title}")
        return None

    def find_best_season_poster(self,
                                title: str,
                                tmdb_id: int,
                                tvdb_id: int,
                                season_number: int,
                                provider_order: List[str],
                                language: Optional[str] = None
                                ) -> Optional[ProviderPoster]:
        for provider in self._get_providers_by_order(provider_order):
            result = self._ask(provider, lambda p=provider: p.get_season_poster(
                season_number=season_number,
                tmdb_id=tmdb_id,
                tvdb_id=tvdb_id,
                language=language
            ), None)
            if result:
                return ProviderPoster(result, provider.name)

        logger.warning(f"No season poster found for {title} season {season_number}")
        return None

    def get_all_posters(self,
                        media_type: str,
                        tmdb_id: Optional[int] = None,
                        tvdb_id: Optional[int] = None,
                        language: Optional[str] = None,
                        provider_name: Optional[str] = None
                        ) -> List[ProviderPoster]:
        all_posters: List[ProviderPoster] = []

        for provider in self._providers_to_ask(provider_name):
            all_posters.extend(self._tag(provider, lambda p=provider: p.get_all_posters(
                media_type=media_type,
                tmdb_id=tmdb_id,
                tvdb_id=tvdb_id,
                language=language,
            )))

        return all_posters

    def get_all_season_posters(self,
                               season_number: int,
                               tmdb_id: Optional[int] = None,
                               tvdb_id: Optional[int] = None,
                               language: Optional[str] = None,
                               provider_name: Optional[str] = None
                               ) -> List[ProviderPoster]:
        all_posters: List[ProviderPoster] = []

        for provider in self._providers_to_ask(provider_name):
            all_posters.extend(self._tag(provider, lambda p=provider: p.get_all_season_posters(
                season_number=season_number,
                tmdb_id=tmdb_id,
                tvdb_id=tvdb_id,
                language=language,
            )))

        return all_posters

    def get_all_collection_posters(self,
                                   collection_id: int,
                                   language: Optional[str] = None,
                                   provider_name: Optional[str] = None
                                   ) -> List[ProviderPoster]:
        all_posters: List[ProviderPoster] = []

        for provider in self._collection_providers(provider_name):
            all_posters.extend(self._tag(provider, lambda p=provider: p.get_all_collection_posters(
                collection_id=collection_id,
                language=language,
            )))

        return all_posters

    def find_collection_id(self, movie_tmdb_ids: List[int]) -> Optional[int]:
        votes: dict[int, int] = {}
        for movie_tmdb_id in movie_tmdb_ids:
            for provider in self._collection_providers(None):
                found = self._ask(provider,
                                  lambda p=provider, m=movie_tmdb_id: p.find_collection_id(m), None)
                if not found:
                    continue
                votes[found] = votes.get(found, 0) + 1
                if votes[found] >= MIN_AGREEING_MEMBERS:
                    return found
        return None

    def _collection_providers(self, provider_name: Optional[str]) -> List[ExternalProvider]:
        return [p for p in self._providers_to_ask(provider_name) if p.supports_collections]

    def get_translated_title(self,
                             media_type: str,
                             language: str,
                             tmdb_id: Optional[int] = None,
                             tvdb_id: Optional[int] = None,
                             season_number: Optional[int] = None,
                             ) -> Optional[str]:
        for provider in self.providers:
            result = self._ask(provider, lambda p=provider: p.get_translated_title(
                media_type=media_type,
                language=language,
                tmdb_id=tmdb_id,
                tvdb_id=tvdb_id,
                season_number=season_number,
            ), None)
            if result:
                return result
        return None

    def _get_provider(self, name: str) -> Optional[ExternalProvider]:
        return next((p for p in self.providers if p.supports(name)), None)

    def _providers_to_ask(self, provider_name: Optional[str]) -> List[ExternalProvider]:
        if not provider_name:
            return list(self.providers)
        provider = self._get_provider(provider_name)
        return [provider] if provider else []

    def _get_providers_by_order(self, provider_order: List[str]) -> List[ExternalProvider]:
        return [p for name in provider_order for p in self.providers if p.supports(name)]

    def _tag(self, provider: ExternalProvider,
             call: Callable[[], Optional[List[str]]]) -> List[ProviderPoster]:
        urls = self._ask(provider, call, []) or []
        last = len(urls) - 1
        return [
            ProviderPoster(url, provider.name, rank=index,
                           rank_score=1.0 if last <= 0 else 1.0 - index / last)
            for index, url in enumerate(urls)
        ]

    def _ask(self, provider: ExternalProvider, call: Callable[[], T], default: T) -> T:
        try:
            return call()
        except Exception:
            logger.warning("Provider '%s' failed this lookup; skipping it", provider.name,
                           exc_info=True)
            return default
