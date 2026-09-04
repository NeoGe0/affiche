from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from affiche.app.mediaserver.library.connector.alchemy_library_connector import AlchemyLibraryConnector
from affiche.app.mediaserver.library.model import ItemStatusFilter, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config import Base

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()
    engine.dispose()

@pytest.fixture
def library_id(session) -> int:
    server = MediaServerPersistenceConnector(session).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    session.flush()
    LibraryService(session).create(Library(
        media_server_id=server.id, external_id="lib", name="Movies",
        type="movie", language="en", enabled=True,
    ))
    session.commit()
    return LibraryService(session).find_libraries(LibrarySearch(media_server_id=server.id))[0].id

def test_status_expands_into_the_listing_predicates():
    unprocessed = LibraryItemSearch(library_id=1, status=ItemStatusFilter.UNPROCESSED)
    assert (unprocessed.processed, unprocessed.has_error) == (False, False)

    errors = LibraryItemSearch(library_id=1, status=ItemStatusFilter.ERRORS)
    assert (errors.processed, errors.has_error) == (None, True)

def test_status_and_raw_predicates_together_are_rejected():
    with pytest.raises(ValidationError):
        LibraryItemSearch(library_id=1, status=ItemStatusFilter.UNPROCESSED, processed=False)

def test_an_unscoped_search_is_rejected_unless_it_is_a_trash_sweep():
    with pytest.raises(ValidationError):
        LibraryItemSearch()

    assert LibraryItemSearch(deleted=True).library_id is None

def test_deleted_before_requires_the_trash_scope():
    with pytest.raises(ValidationError):
        LibraryItemSearch(library_id=1, deleted_before=datetime.now(timezone.utc))

def test_a_default_search_excludes_trashed_items(session, library_id):
    connector = AlchemyLibraryConnector(session)
    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id="live", title="Live", type="movie"),
        LibraryItem(library_id=library_id, external_id="gone", title="Gone", type="movie"),
    ])
    gone = next(i for i in connector.find_items(LibraryItemSearch(library_id=library_id))
                if i.external_id == "gone")
    gone.deleted_at = datetime.now(timezone.utc)
    connector.update_item(gone)

    live_only = connector.find_items(LibraryItemSearch(library_id=library_id))
    assert [i.external_id for i in live_only] == ["live"]

    trash_only = connector.find_items(LibraryItemSearch(library_id=library_id, deleted=True))
    assert [i.external_id for i in trash_only] == ["gone"]

    assert connector.count_items(LibraryItemSearch(library_id=library_id)) == 1

def test_page_size_zero_cannot_reach_the_query():
    with pytest.raises(ValidationError):
        LibraryItemSearch(library_id=1, page_size=0)
