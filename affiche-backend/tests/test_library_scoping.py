from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.model import LibraryItemSearch, SortDir

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

def _server(session: Session, name: str) -> MediaServer:
    entity = MediaServerPersistenceConnector(session).create(MediaServer(
        name=name, type=MediaServerType.PLEX, url="http://localhost:32400", token="t",
    ))
    session.flush()
    return MediaServer.model_validate(entity)

def _library(session: Session, server: MediaServer, external_id: str) -> Library:
    service = LibraryService(session)
    service.create(Library(
        media_server_id=server.id, external_id=external_id, name="Movies",
        type="movie", language="en", enabled=True,
    ))
    session.flush()
    return service.find_libraries(LibrarySearch(media_server_id=server.id))[0]

@pytest.fixture
def two_servers(session: Session):
    a, b = _server(session, "A"), _server(session, "B")
    return (a, _library(session, a, "lib-a")), (b, _library(session, b, "lib-b"))

class TestDeleteLibraryScoping:
    def test_deletes_a_library_of_the_named_server(self, session: Session, two_servers):
        (server, library), _ = two_servers
        service = LibraryService(session)

        assert service.delete_library(server.id, library.id) is True
        assert service.find_libraries(LibrarySearch(media_server_id=server.id)) == []

    def test_refuses_a_library_belonging_to_another_server(self, session: Session, two_servers):
        (server_a, _), (server_b, library_b) = two_servers
        service = LibraryService(session)

        assert service.delete_library(server_a.id, library_b.id) is False
        assert [lib.id for lib in service.find_libraries(LibrarySearch(media_server_id=server_b.id))] == [library_b.id]

    def test_unknown_library_reports_false(self, session: Session, two_servers):
        (server, _), _ = two_servers

        assert LibraryService(session).delete_library(server.id, 9999) is False

class TestRestoreItem:
    def _trashed_item(self, session: Session, library: Library) -> LibraryItem:
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="gone", title="Movie", type="movie",
            last_seen_at=T0,
        )])
        session.flush()
        service.reconcile_deletions(library.id, T0 + timedelta(hours=1))
        session.expire_all()
        return service.find_items(LibraryItemSearch(library_id=library.id, deleted=True, sort_by='deleted_at', sort_dir=SortDir.DESC))[0]

    def test_restores_a_trashed_item(self, session: Session, two_servers):
        (server, library), _ = two_servers
        item = self._trashed_item(session, library)
        service = LibraryService(session)

        restored = service.restore_item(server.id, library.id, item.id)
        session.expire_all()

        assert restored is not None
        assert service.count_items(LibraryItemSearch(library_id=library.id, deleted=True)) == 0
        assert [i.external_id for i in service.find_items(LibraryItemSearch(library_id=library.id))] == ["gone"]

    def test_refuses_an_item_that_is_not_in_the_trash(self, session: Session, two_servers):
        (server, library), _ = two_servers
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="live", title="Movie", type="movie",
        )])
        session.flush()
        live = service.find_items(LibraryItemSearch(library_id=library.id, external_ids=["live"]))[0]

        assert service.restore_item(server.id, library.id, live.id) is None
