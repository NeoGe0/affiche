import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional, Sequence

from sqlalchemy.orm import Session

from affiche.app.filestore.filestore import FileStoreService
from affiche.app.mediaserver.library.model import (
    Library, LibraryItem, LibraryItemSearch, LibraryItemStats,
    LibrarySearch,
)
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.episodes.library_episode_service import LibraryEpisodeService
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.sync.reidentification import (
    RemoteIdentity,
    SplitItem,
    match_readded_items,
    match_split_items,
)
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.service_configuration.service.configuration_repository import ConfigurationRepository
from affiche.config.app_settings_store import AppSettingsStore

logger = logging.getLogger(__name__)

class LibraryService:

    def __init__(self,
                 session: Session,
                 file_store: Optional[FileStoreService] = None,
                 app_settings_store: Optional[AppSettingsStore] = None):
        self.configuration_repo = ConfigurationRepository(session)
        self.library_repo = LibraryRepository(session)
        self.library_settings_service = LibrarySettingsService(session)
        self.library_season_service = LibrarySeasonService(session)
        self.library_episode_service = LibraryEpisodeService(session)
        self.file_store = file_store
        self.app_settings_store = app_settings_store

    def create(self, library: Library):
        created_library = self.library_repo.create_library(library)
        self.library_settings_service.create_settings(library_id=created_library.id)

    def create_or_update_items_batch(self, items: List[LibraryItem]):
        self.library_repo.create_or_update_items_batch(items)

    def get_library(self,
                    media_server_id: int,
                    library_id: int) -> Library:
        return self.library_repo.get_library(media_server_id=media_server_id, library_id=library_id)

    def get_library_item(self,
                         media_server_id: int,
                         library_id: int,
                         item_id: int) -> LibraryItem:
        self.get_library(media_server_id=media_server_id, library_id=library_id)
        return self.library_repo.get_library_item(library_id, item_id)

    def find_libraries(self, search: LibrarySearch) -> List[Library]:
        return self.library_repo.find_libraries(search)

    def find_items(self, search: LibraryItemSearch) -> List[LibraryItem]:
        return self.library_repo.find_items(search)

    def count_items(self, search: LibraryItemSearch) -> int:
        return self.library_repo.count_items(search)

    def count_items_per_library(self, search: LibraryItemSearch) -> dict[int, int]:
        return self.library_repo.count_items_per_library(search)

    def count_status_buckets(self, search: LibraryItemSearch) -> LibraryItemStats:
        return self.library_repo.count_status_buckets(search)

    def count_buckets_per_library(self, search: LibraryItemSearch) -> dict[int, LibraryItemStats]:
        return self.library_repo.count_buckets_per_library(search)

    def count_items_by_provider(self, search: LibraryItemSearch) -> dict[Optional[str], int]:
        return self.library_repo.count_items_by_provider(search)

    def count_posters_by_provider(self, search: LibraryItemSearch) -> dict[Optional[str], int]:
        return self.library_repo.count_posters_by_provider(search)

    def set_item_locked(self,
                        media_server_id: int,
                        library_id: int,
                        item_id: int,
                        locked: bool) -> LibraryItem:
        item = self.get_library_item(media_server_id, library_id, item_id)
        item.locked = locked
        return self.library_repo.create_or_update_item(item)

    def set_items_locked(self,
                         media_server_id: int,
                         item_ids: List[int],
                         locked: bool) -> int:
        libraries = self.find_libraries(LibrarySearch(media_server_id=media_server_id))
        if not libraries or not item_ids:
            return 0

        items = self.library_repo.find_items(LibraryItemSearch(
            library_ids=[library.id for library in libraries], item_ids=item_ids))

        changed = 0
        for item in items:
            if item.locked == locked:
                continue
            item.locked = locked
            self.library_repo.create_or_update_item(item)
            changed += 1
        return changed

    def letter_offsets(self, search: LibraryItemSearch) -> List[tuple[str, int]]:
        return self.library_repo.letter_offsets(search)

    def get_item_seasons(self, library_id: int, item_id: int) -> List:
        return self.library_season_service.get_item_seasons(library_id, item_id)

    def get_season_episodes(self, library_id: int, item_id: int, season_number: int) -> List:
        seasons = self.library_season_service.get_item_seasons(library_id, item_id)
        season = next((s for s in seasons if s.season_number == season_number), None)
        if season is None or season.id is None:
            return []
        return self.library_episode_service.get_season_episodes(season.id)

    def delete_library(self, media_server_id: int, library_id: int) -> bool:
        if not self.library_repo.delete_library(media_server_id, library_id):
            return False
        self.delete_library_poster_files(library_id)
        return True

    def delete_library_poster_files(self, library_id: int) -> None:
        if self.file_store is None:
            return
        try:
            self.file_store.delete_library(library_id)
        except OSError:
            logger.exception("Failed to delete poster files for library %s", library_id)

    def adopt_readded_items(self,
                            library_id: int,
                            incoming: Sequence[RemoteIdentity]) -> tuple[int, int]:
        existing = self.library_repo.find_items(LibraryItemSearch(
            library_id=library_id, deleted=None))

        adoptions = match_readded_items(existing, incoming)
        if adoptions:
            logger.info("Library %s: %d item(s) re-added under a new id, adopting them",
                        library_id, len(adoptions))
            self.library_repo.rekey_items(adoptions)

        return len(adoptions), self._merge_split_items(library_id, existing, incoming)

    def _merge_split_items(self,
                           library_id: int,
                           existing: List[LibraryItem],
                           incoming: Sequence[RemoteIdentity]) -> int:
        by_id = {item.id: item for item in existing}
        return sum(self._merge_split(library_id, split, by_id)
                   for split in match_split_items(existing, incoming))

    def _merge_split(self, library_id: int, split: SplitItem,
                     by_id: dict[int, LibraryItem]) -> bool:
        fresh = by_id[split.fresh_id]
        if fresh.processed or fresh.locked or fresh.poster_hash or fresh.error_message:
            logger.info("Library %s: item %s (%s) matches trashed item %s, but has work of its "
                        "own — leaving both alone",
                        library_id, fresh.id, fresh.title, split.stale_id)
            return False
        logger.info("Library %s: item %s (%s) is the re-added twin of trashed item %s, merging",
                    library_id, fresh.id, fresh.title, split.stale_id)
        self._delete_item_poster_files(fresh)
        self.library_repo.hard_delete_items([fresh.id])
        self.library_repo.rekey_items({split.stale_id: split.external_id})
        return True

    def merge_readded_twin(self,
                           library_id: int,
                           identity: RemoteIdentity,
                           is_gone: Callable[[str], bool]) -> Optional[int]:
        existing = self.library_repo.find_items(LibraryItemSearch(
            library_id=library_id, deleted=None))
        splits = match_split_items(existing, [identity])
        if not splits:
            return None

        split = splits[0]
        by_id = {item.id: item for item in existing}
        if not is_gone(by_id[split.stale_id].external_id):
            return None
        if not self._merge_split(library_id, split, by_id):
            return None

        self.library_repo.restore_item(library_id, split.stale_id)
        return split.stale_id

    def reconcile_deletions(self, library_id: int, seen_at: datetime) -> tuple[int, int]:
        return self.library_repo.reconcile_deletions(library_id, seen_at)

    def restore_item(self, media_server_id: int, library_id: int, item_id: int) -> Optional[LibraryItem]:
        self.get_library(media_server_id=media_server_id, library_id=library_id)
        return self.library_repo.restore_item(library_id, item_id)

    def purge_deleted_items(self,
                            library_id: Optional[int] = None,
                            older_than: Optional[datetime] = None) -> int:
        items = self.library_repo.find_items(LibraryItemSearch(
            library_id=library_id, deleted=True, deleted_before=older_than))
        if not items:
            return 0

        for item in items:
            self._delete_item_poster_files(item)

        purged = self.library_repo.hard_delete_items([item.id for item in items])
        logger.info("Purged %d trashed item(s)%s", purged,
                    f" from library {library_id}" if library_id is not None else "")
        return purged

    def purge_expired_trash(self) -> int:
        retention_days = self._trash_retention_days()
        older_than = datetime.now(timezone.utc) - timedelta(days=retention_days)
        return self.purge_deleted_items(older_than=older_than)

    def _trash_retention_days(self) -> int:
        if self.app_settings_store is None:
            return 30
        return self.app_settings_store.get().trash_retention_days

    def _delete_item_poster_files(self, item: LibraryItem) -> None:
        if self.file_store is None:
            return
        try:
            self.file_store.delete(item.library_id, item.id)
            if item.type == 'show':
                for season in self.library_season_service.get_item_seasons(item.library_id, item.id):
                    self.file_store.delete(item.library_id, item.id, season_number=season.season_number)
        except Exception:
            logger.exception("Failed to delete poster files for item %s (library %s)", item.id, item.library_id)
