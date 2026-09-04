from functools import reduce
from typing import List

from sqlalchemy.orm import Session

from affiche.app.dashboard.model.dashboard import DashboardLibrary, DashboardSummary, ProviderShare
from affiche.app.mediaserver.library.model import LibraryItemSearch, LibraryItemStats, LibrarySearch
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository

class DashboardService:

    def __init__(self, session: Session):
        self._library_repo = LibraryRepository(session)
        self._media_server_repo = MediaServerRepository(session)

    def get_summary(self) -> DashboardSummary:
        media_servers = self._media_server_repo.find_all()
        libraries = [(server, library)
                     for server in media_servers
                     for library in self._library_repo.find_libraries(LibrarySearch(media_server_id=server.id))]

        if not libraries:
            return DashboardSummary(totals=LibraryItemStats(), library_count=0,
                                    media_server_count=len(media_servers),
                                    libraries=[], providers=[])

        search = LibraryItemSearch(library_ids=[library.id for _, library in libraries])
        stats_by_library = self._library_repo.count_buckets_per_library(search)
        providers = self._library_repo.count_posters_by_provider(search)

        rows = [
            DashboardLibrary(
                library_id=library.id,
                library_name=library.name,
                library_type=library.type,
                enabled=library.enabled,
                media_server_id=server.id,
                media_server_name=server.name,
                media_server_type=server.type,
                stats=stats_by_library.get(library.id, LibraryItemStats()),
            )
            for server, library in libraries
        ]

        return DashboardSummary(
            totals=self._sum(row.stats for row in rows),
            library_count=len(rows),
            media_server_count=len(media_servers),
            libraries=rows,
            providers=self._provider_shares(providers),
        )

    @staticmethod
    def _sum(stats) -> LibraryItemStats:
        return reduce(lambda a, b: a + b, stats, LibraryItemStats())

    @staticmethod
    def _provider_shares(counts: dict) -> List[ProviderShare]:
        named = {provider: count for provider, count in counts.items() if provider is not None}
        return [ProviderShare(provider=provider, count=count)
                for provider, count in sorted(named.items(), key=lambda kv: (-kv[1], kv[0]))]
