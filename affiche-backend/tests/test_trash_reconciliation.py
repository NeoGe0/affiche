from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.model import LibraryItemSearch, SortDir

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

@pytest.fixture
def media_server(session: Session):
    connector = MediaServerPersistenceConnector(session)
    entity = connector.create(MediaServer(
        name="Test Server", type=MediaServerType.PLEX,
        url="http://localhost:32400", token="test-token",
    ))
    session.flush()
    return MediaServer.model_validate(entity)

@pytest.fixture
def library(session: Session, media_server):
    service = LibraryService(session)
    service.create(Library(
        media_server_id=media_server.id, external_id="lib-1", name="Movies",
        type="movie", language="en", enabled=True,
    ))
    session.flush()
    return service.find_libraries(LibrarySearch(media_server_id=media_server.id))[0]

def _seed(service, library_id, external_id, seen_at, title="Movie"):
    service.create_or_update_items_batch([LibraryItem(
        library_id=library_id, external_id=external_id, title=title,
        type="movie", last_seen_at=seen_at,
    )])

class TestReconcileDeletions:
    def test_soft_deletes_items_not_seen_this_run(self, session: Session, library):
        service = LibraryService(session)
        for ext in ("a", "b", "c"):
            _seed(service, library.id, ext, T0)
        session.flush()

        t1 = T0 + timedelta(hours=1)
        _seed(service, library.id, "a", t1)
        _seed(service, library.id, "b", t1)
        session.flush()

        soft, restored = service.reconcile_deletions(library.id, t1)
        session.expire_all()

        assert (soft, restored) == (1, 0)
        assert {i.external_id for i in service.find_items(LibraryItemSearch(library_id=library.id))} == {"a", "b"}
        assert service.count_items(LibraryItemSearch(library_id=library.id)) == 2
        deleted = service.find_items(LibraryItemSearch(library_id=library.id, deleted=True, sort_by='deleted_at', sort_dir=SortDir.DESC))
        assert [i.external_id for i in deleted] == ["c"]
        assert deleted[0].deleted_at is not None

    def test_restores_reappeared_item(self, session: Session, library):
        service = LibraryService(session)
        _seed(service, library.id, "c", T0)
        session.flush()

        t1 = T0 + timedelta(hours=1)
        service.reconcile_deletions(library.id, t1)
        session.expire_all()
        assert service.count_items(LibraryItemSearch(library_id=library.id, deleted=True)) == 1

        t2 = T0 + timedelta(hours=2)
        _seed(service, library.id, "c", t2)
        session.flush()
        soft, restored = service.reconcile_deletions(library.id, t2)
        session.expire_all()

        assert (soft, restored) == (0, 1)
        assert service.count_items(LibraryItemSearch(library_id=library.id, deleted=True)) == 0
        assert {i.external_id for i in service.find_items(LibraryItemSearch(library_id=library.id))} == {"c"}

    def test_get_items_by_external_ids_excludes_soft_deleted(self, session: Session, library):
        service = LibraryService(session)
        _seed(service, library.id, "s", T0, title="Show")
        session.flush()
        service.reconcile_deletions(library.id, T0 + timedelta(hours=1))
        session.expire_all()

        assert service.find_items(LibraryItemSearch(library_id=library.id, external_ids=["s"])) == []

class TestPurge:
    def test_empty_trash_hard_deletes_all_soft_deleted(self, session: Session, library):
        service = LibraryService(session)
        _seed(service, library.id, "gone", T0)
        session.flush()
        service.reconcile_deletions(library.id, T0 + timedelta(hours=1))
        session.expire_all()
        assert service.count_items(LibraryItemSearch(library_id=library.id, deleted=True)) == 1

        purged = service.purge_deleted_items(library_id=library.id)
        session.expire_all()

        assert purged == 1
        assert service.count_items(LibraryItemSearch(library_id=library.id, deleted=True)) == 0

    def test_purge_respects_older_than(self, session: Session, library):
        service = LibraryService(session)
        _seed(service, library.id, "old", T0)
        session.flush()
        t_old = T0 + timedelta(days=1)
        service.reconcile_deletions(library.id, t_old)

        t_new = T0 + timedelta(days=40)
        _seed(service, library.id, "new", T0 + timedelta(days=39))
        session.flush()
        service.reconcile_deletions(library.id, t_new)
        session.expire_all()
        assert service.count_items(LibraryItemSearch(library_id=library.id, deleted=True)) == 2

        cutoff = T0 + timedelta(days=30)
        purged = service.purge_deleted_items(older_than=cutoff)
        session.expire_all()

        assert purged == 1
        remaining = service.find_items(LibraryItemSearch(library_id=library.id, deleted=True, sort_by='deleted_at', sort_dir=SortDir.DESC))
        assert [i.external_id for i in remaining] == ["new"]
