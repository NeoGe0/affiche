import logging
from datetime import datetime, timezone

from affiche.app.asynch.async_task_service import report_task_progress
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.mediaserver.library import LibraryService
from affiche.app.mediaserver.library.model import Library, LibraryEpisode, LibraryItem, LibrarySearch, LibrarySeason
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.episodes.library_episode_service import LibraryEpisodeService
from affiche.app.mediaserver.library.collections.library_collection_service import LibraryCollectionService
from affiche.app.mediaserver.library.settings import LibrarySettingsService
from affiche.app.mediaserver.library.sync.incremental import RECENT_ITEM_LIMIT
from affiche.app.mediaserver.library.sync.reidentification import RemoteIdentity
from affiche.app.mediaserver.model.media_server import MediaServer
from affiche.app.mediaserver.service.media_server_connector_factory import MediaServerConnectorFactory
from affiche.external.media_quality import MEDIA_FIELDS
from affiche.external.jellyfin.service.jellyfin_service import JellyfinService

from affiche.app.mediaserver.library.model import LibraryItemSearch

logger = logging.getLogger(__name__)

class JellyfinSynchronisationService:
    BATCH_SIZE = 100

    def __init__(self,
                 library_service: LibraryService,
                 library_settings_service: LibrarySettingsService,
                 library_season_service: LibrarySeasonService,
                 library_episode_service: LibraryEpisodeService,
                 library_collection_service: LibraryCollectionService,
                 file_store: FileStoreService,
                 connector_factory: MediaServerConnectorFactory):
        self.library_service = library_service
        self.library_settings_service = library_settings_service
        self.season_service = library_season_service
        self.episode_service = library_episode_service
        self.collection_service = library_collection_service
        self.file_store = file_store
        self._connector_factory = connector_factory

    def _collections_tracked(self, library: Library) -> bool:
        return self.library_settings_service.get_settings_or_default(library.id).track_collections

    def _episodes_tracked(self, library: Library) -> bool:
        return self.library_settings_service.get_settings_or_default(library.id).track_episodes

    def _connector(self, media_server: MediaServer) -> JellyfinService:
        connector = self._connector_factory.get(media_server.id)
        if not isinstance(connector, JellyfinService):
            raise ValueError(f"Media server {media_server.id} is not a Jellyfin server")
        return connector

    def sync_jellyfin_libraries(self,
                                media_server: MediaServer,
                                cancel_check=None):
        logger.info("Starting Jellyfin library sync")
        jellyfin_service = self._connector(media_server)
        libraries = self.library_service.find_libraries(LibrarySearch(media_server_id=media_server.id))

        logger.info("Found %d libraries to sync", len(libraries))

        for library in libraries:
            if cancel_check and cancel_check():
                logger.info("Jellyfin library sync cancelled")
                break
            if library.enabled:
                try:
                    self._sync_single_library(jellyfin_service, library, cancel_check=cancel_check)
                except Exception:
                    logger.exception("Failed to sync library '%s'", library.name)

        if not (cancel_check and cancel_check()):
            self.library_service.purge_expired_trash()

        logger.info("Jellyfin library sync completed")

    def sync_jellyfin_library(self,
                              media_server: MediaServer,
                              library_id: int,
                              cancel_check=None,
                              incremental: bool = False):
        logger.info("Starting Jellyfin library %s %s sync", library_id,
                    "incremental" if incremental else "full")
        jellyfin_service = self._connector(media_server)
        library = self.library_service.get_library(media_server.id, library_id)
        self._sync_single_library(jellyfin_service, library, cancel_check=cancel_check,
                                  incremental=incremental)

        logger.info("Jellyfin library sync completed")

    def sync_jellyfin_item(self, media_server: MediaServer, library_id: int, item_id: int):
        library = self.library_service.get_library(media_server.id, library_id)
        db_item = self.library_service.get_library_item(media_server.id, library_id, item_id)

        jellyfin_service = self._connector(media_server)
        fetched = jellyfin_service.get_library_item(db_item.external_id, library.external_id)
        if not fetched:
            logger.info("[sync] item %s (%s) no longer on Jellyfin", item_id, db_item.title)
            return None

        synced_id = self.library_service.merge_readded_twin(
            library.id,
            RemoteIdentity(external_id=str(fetched.id), type=fetched.type,
                           imdb_id=fetched.imdb_id, tmdb_id=fetched.tmdb_id,
                           tvdb_id=fetched.tvdb_id),
            is_gone=lambda external_id: jellyfin_service.get_library_item(
                external_id, library.external_id) is None,
        ) or item_id

        self.library_service.create_or_update_items_batch([
            LibraryItem(
                external_id=str(fetched.id),
                library_id=library.id,
                title=fetched.title,
                type=fetched.type,
                year=fetched.year,
                release_date=fetched.release_date,
                added_at=fetched.added_at,
                updated_at=fetched.updated_at,
                last_seen_at=datetime.now(timezone.utc),
                imdb_id=fetched.imdb_id,
                tmdb_id=fetched.tmdb_id,
                tvdb_id=fetched.tvdb_id,
                **{field: getattr(fetched, field) for field in MEDIA_FIELDS},
            )
        ])
        if fetched.type == 'show':
            self._sync_seasons(jellyfin_service, library, [fetched])
            if self._episodes_tracked(library):
                self._sync_episodes(jellyfin_service, library, [fetched])

        logger.info("[sync] item %s (%s): metadata synced", item_id, fetched.title)
        return self.library_service.get_library_item(media_server.id, library_id, synced_id)

    def _fetch_items(self, jellyfin_service: JellyfinService, library: Library,
                     incremental: bool):
        if not incremental:
            return jellyfin_service.get_library_items(library.external_id), False

        items = jellyfin_service.get_recently_added_items(library.external_id, RECENT_ITEM_LIMIT)
        if len(items) < RECENT_ITEM_LIMIT:
            return items, True

        logger.info("Library '%s': %d recently added items filled the window — syncing in full",
                    library.name, len(items))
        return jellyfin_service.get_library_items(library.external_id), False

    def _sync_single_library(self,
                             jellyfin_service: JellyfinService,
                             library: Library,
                             cancel_check=None,
                             incremental: bool = False):

        logger.info("Started syncing library '%s'", library.name)
        library_items, incremental = self._fetch_items(jellyfin_service, library, incremental)
        logger.info("Processing library '%s' with %d items%s", library.name, len(library_items),
                    " (recently added)" if incremental else "")

        if library_items:
            self.library_service.adopt_readded_items(library.id, [
                RemoteIdentity(external_id=str(item.id), type=item.type, imdb_id=item.imdb_id,
                               tmdb_id=item.tmdb_id, tvdb_id=item.tvdb_id)
                for item in library_items
            ])

        seen_at = datetime.now(timezone.utc)
        batch = []
        shows_to_sync = []

        total = len(library_items)
        progress_label = f"Syncing metadata — {library.name}"
        progress_step = max(1, total // 100)
        report_task_progress(0, total, progress_label)

        for index, item in enumerate(library_items, start=1):
            if cancel_check and cancel_check():
                logger.info("Sync cancelled for library '%s'", library.name)
                return
            if index % progress_step == 0 or index == total:
                report_task_progress(index, total, progress_label)
            try:
                to_create = LibraryItem(
                    external_id=str(item.id),
                    library_id=library.id,
                    title=item.title,
                    type=item.type,
                    year=item.year,
                    release_date=item.release_date,
                    added_at=item.added_at,
                    updated_at=item.updated_at,
                    last_seen_at=seen_at,
                    imdb_id=item.imdb_id,
                    tmdb_id=item.tmdb_id,
                    tvdb_id=item.tvdb_id,
                    **{field: getattr(item, field) for field in MEDIA_FIELDS},
                )
            except Exception:
                logger.exception("[sync] item %s (%s): FAILED to map", item.id, item.title)
                continue

            logger.debug("[sync] item %s (%s): mapped", item.id, item.title)
            batch.append(to_create)

            if item.type == 'show':
                shows_to_sync.append(item)

            if len(batch) >= self.BATCH_SIZE:
                self.library_service.create_or_update_items_batch(batch)
                batch = []

        if batch:
            self.library_service.create_or_update_items_batch(batch)

        logger.info("Finished syncing library '%s' with %d items", library.name, len(library_items))

        if shows_to_sync and not (cancel_check and cancel_check()):
            self._sync_seasons(jellyfin_service, library, shows_to_sync)
            if self._episodes_tracked(library) and not (cancel_check and cancel_check()):
                self._sync_episodes(jellyfin_service, library, shows_to_sync)

        if incremental or (cancel_check and cancel_check()):
            return

        if self._collections_tracked(library):
            self._sync_collections(jellyfin_service, library, seen_at)

        if library_items and not (cancel_check and cancel_check()):
            soft, restored = self.library_service.reconcile_deletions(library.id, seen_at)
            logger.info("Reconciled library '%s': soft-deleted %d, restored %d", library.name, soft, restored)

        if not (cancel_check and cancel_check()):
            self.library_settings_service.mark_full_sync(library.id, seen_at)

    def _sync_collections(self, jellyfin_service: JellyfinService, library: Library, seen_at):
        try:
            collections = jellyfin_service.get_collections(library.external_id)
        except Exception:
            logger.exception("Failed to fetch collections for library '%s'", library.name)
            return

        self.collection_service.sync_collections(
            library.id,
            [c.model_dump() | {'external_id': c.id} for c in collections],
            seen_at,
            drop_empty=True,
        )

    def _sync_seasons(self, jellyfin_service: JellyfinService, library: Library, shows: list):
        logger.info("Syncing seasons for %d shows", len(shows))

        show_external_ids = [str(show.id) for show in shows]
        internal_shows = self.library_service.find_items(LibraryItemSearch(
            library_id=library.id, external_ids=show_external_ids, deleted=None))
        external_to_internal = {item.external_id: item.id for item in internal_shows}

        season_batch = []
        total_seasons = 0

        for show in shows:
            try:
                internal_show_id = external_to_internal.get(str(show.id))
                if not internal_show_id:
                    logger.warning("Could not find internal ID for show %s", show.id)
                    continue

                jellyfin_seasons = jellyfin_service.get_show_seasons(str(show.id), library.external_id)

                rekeyed = self.season_service.adopt_readded_seasons(
                    library.id, internal_show_id,
                    {season.season_number: str(season.id) for season in jellyfin_seasons})
                if rekeyed:
                    self.episode_service.delete_episodes_of_seasons(rekeyed)

                for jellyfin_season in jellyfin_seasons:
                    season = LibrarySeason(
                        external_id=str(jellyfin_season.id),
                        show_id=internal_show_id,
                        library_id=library.id,
                        season_number=jellyfin_season.season_number,
                        title=jellyfin_season.title,
                        added_at=jellyfin_season.added_at,
                        updated_at=jellyfin_season.updated_at,
                        imdb_id=jellyfin_season.imdb_id,
                        tmdb_id=jellyfin_season.tmdb_id,
                        tvdb_id=jellyfin_season.tvdb_id,
                        poster_url=jellyfin_season.poster_url,
                    )
                    season_batch.append(season)
                    total_seasons += 1

                    if len(season_batch) >= self.BATCH_SIZE:
                        self.season_service.create_or_update(season_batch)
                        season_batch = []

            except Exception:
                logger.exception("Failed to sync seasons for show %s", show.id)

        if season_batch:
            self.season_service.create_or_update(season_batch)

        logger.info("Finished syncing %d seasons", total_seasons)

    def _sync_episodes(self, jellyfin_service: JellyfinService, library: Library, shows: list):
        logger.info("Syncing episodes for %d shows", len(shows))

        show_external_ids = [str(show.id) for show in shows]
        internal_shows = self.library_service.find_items(LibraryItemSearch(
            library_id=library.id, external_ids=show_external_ids, deleted=None))
        external_to_internal = {item.external_id: item.id for item in internal_shows}

        episode_batch = []
        total_episodes = 0

        for show in shows:
            try:
                internal_show_id = external_to_internal.get(str(show.id))
                if not internal_show_id:
                    continue

                seasons = self.season_service.get_item_seasons(library.id, internal_show_id)
                season_ext_to_id = {s.external_id: s.id for s in seasons}

                jellyfin_episodes = jellyfin_service.get_show_episodes(str(show.id), library.external_id)
                for ep in jellyfin_episodes:
                    season_id = season_ext_to_id.get(str(ep.season_external_id))
                    if not season_id:
                        continue
                    episode_batch.append(LibraryEpisode(
                        external_id=str(ep.id),
                        season_id=season_id,
                        show_id=internal_show_id,
                        library_id=library.id,
                        season_number=ep.season_number,
                        episode_number=ep.episode_number,
                        title=ep.title,
                        air_date=ep.air_date,
                        added_at=ep.added_at,
                        updated_at=ep.updated_at,
                        imdb_id=ep.imdb_id,
                        tmdb_id=ep.tmdb_id,
                        tvdb_id=ep.tvdb_id,
                        **{field: getattr(ep, field) for field in MEDIA_FIELDS},
                    ))
                    total_episodes += 1

                    if len(episode_batch) >= self.BATCH_SIZE:
                        self.episode_service.create_or_update(episode_batch)
                        episode_batch = []

            except Exception:
                logger.exception("Failed to sync episodes for show %s", show.id)

        if episode_batch:
            self.episode_service.create_or_update(episode_batch)

        logger.info("Finished syncing %d episodes", total_episodes)
