import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.collections.library_collection_service import (
    LibraryCollectionService,
)
from affiche.app.mediaserver.library.collections.model.library_collection import (
    LibraryCollectionSearch,
)
from affiche.app.mediaserver.library.model import (
    Library,
    LibraryItem,
    LibraryItemSearch,
    SearchCriteria,
    SortDir,
    LibrarySearch,
)
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.provider_stats import RETENTION_DAYS, ProviderStatsQuery
from affiche.app.search import GlobalItemSearch
from affiche.app.task_history import TaskRunSearch
from affiche.config import Base

CRITERIA = {
    LibraryItemSearch: {"library_id": 1},
    LibraryCollectionSearch: {"library_id": 1},
    LibrarySearch: {"media_server_id": 1},
    GlobalItemSearch: {},
    TaskRunSearch: {},
    ProviderStatsQuery: {},
}

SCOPED = [LibraryItemSearch, LibraryCollectionSearch, LibrarySearch]

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()

@pytest.fixture
def library(db):
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    db.flush()
    service = LibraryService(db)
    service.create(Library(media_server_id=server.id, external_id="sec-1", name="Movies",
                           type="movie", language="en", enabled=True))
    db.commit()
    stored = service.find_libraries(LibrarySearch(media_server_id=server.id))[0]
    service.create_or_update_items_batch([
        LibraryItem(library_id=stored.id, external_id=external, title=title, type="movie")
        for external, title in [("100", "Alien"), ("200", "Bambi"), ("300", "Dune")]
    ])
    db.commit()
    return stored

@pytest.mark.parametrize("criteria,scope", [(c, s) for c, s in CRITERIA.items()
                                            if c is not ProviderStatsQuery])
def test_every_criteria_object_shares_one_paging_vocabulary(criteria, scope):
    assert issubclass(criteria, SearchCriteria)

    search = criteria(**scope, page=3, page_size=25)

    assert search.offset == 75
    assert search.limit == 25

@pytest.mark.parametrize("criteria,scope", [(c, s) for c, s in CRITERIA.items()
                                            if c is not ProviderStatsQuery])
def test_an_unpaged_search_asks_for_everything(criteria, scope):
    search = criteria(**scope)

    assert search.page_size is None
    assert search.limit is None
    assert search.offset == 0

@pytest.mark.parametrize("criteria,scope", list(CRITERIA.items()))
def test_criteria_are_frozen(criteria, scope):
    search = criteria(**scope)

    with pytest.raises(Exception):
        search.page = 4

@pytest.mark.parametrize("criteria", SCOPED)
def test_a_scoped_search_refuses_to_be_built_without_its_scope(criteria):
    with pytest.raises(ValueError):
        criteria()

def test_the_readers_that_span_everything_need_no_scope():
    assert GlobalItemSearch(search="x").page == 0
    assert TaskRunSearch().sort_dir is SortDir.DESC

def test_a_provider_stats_window_cannot_ask_past_retention():
    assert ProviderStatsQuery(days=RETENTION_DAYS).days == RETENTION_DAYS
    with pytest.raises(ValueError):
        ProviderStatsQuery(days=RETENTION_DAYS + 1)

def test_a_trash_sweep_is_the_one_unscoped_item_read():
    assert LibraryItemSearch(deleted=True).library_id is None

def test_collections_can_be_listed_descending(db, library):
    service = LibraryCollectionService(db)
    service.sync_collections(library.id, [
        {'external_id': 'c1', 'title': 'Alien Saga', 'member_external_ids': ['100']},
        {'external_id': 'c2', 'title': 'Bambi Saga', 'member_external_ids': ['200']},
        {'external_id': 'c3', 'title': 'Dune Saga', 'member_external_ids': ['300']},
    ])

    def titles(sort_dir):
        return [c.title for c in service.find_collections(
            LibraryCollectionSearch(library_id=library.id, sort_by='title', sort_dir=sort_dir))]

    assert titles(SortDir.ASC) == ["Alien Saga", "Bambi Saga", "Dune Saga"]
    assert titles(SortDir.DESC) == ["Dune Saga", "Bambi Saga", "Alien Saga"]

def test_items_and_collections_page_the_same_way(db, library):
    service = LibraryCollectionService(db)
    service.sync_collections(library.id, [
        {'external_id': f'c{n}', 'title': title, 'member_external_ids': []}
        for n, title in enumerate(["Alien Saga", "Bambi Saga", "Dune Saga"])
    ])

    items = LibraryService(db).find_items(
        LibraryItemSearch(library_id=library.id, page=1, page_size=2))
    collections = service.find_collections(
        LibraryCollectionSearch(library_id=library.id, page=1, page_size=2))

    assert [i.title for i in items] == ["Dune"]
    assert [c.title for c in collections] == ["Dune Saga"]
