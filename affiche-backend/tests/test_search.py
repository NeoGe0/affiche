import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.search import GlobalItemSearch, SearchService
from affiche.config import Base
from affiche.config.database import SessionLocal

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

def _seed(session, server_name: str, libraries: dict[str, list[str]],
          server_type: MediaServerType = MediaServerType.PLEX) -> None:
    server = MediaServerPersistenceConnector(session).create(MediaServer(
        name=server_name, type=server_type, url="http://x", token="t",
    ))
    session.flush()
    service = LibraryService(session)

    for index, (library_name, titles) in enumerate(libraries.items()):
        service.create(Library(media_server_id=server.id, external_id=f"{server_name}-{index}",
                               name=library_name, type="movie", language="en",
                               enabled=True))
        session.commit()
        library = next(lib for lib in service.find_libraries(LibrarySearch(media_server_id=server.id)) if lib.name == library_name)

        service.create_or_update_items_batch([
            LibraryItem(library_id=library.id, external_id=f"{library.id}-{i}",
                        title=title, type="movie")
            for i, title in enumerate(titles)
        ])
        session.commit()

def test_an_empty_install_matches_nothing_rather_than_failing(db):
    results = SearchService(db).search_items(GlobalItemSearch(search="alien", page=0, page_size=25))

    assert (results.hits, results.total) == ([], 0)

def test_a_match_is_found_in_any_library_of_any_server(db):
    _seed(db, "Plex", {"Movies": ["Alien"], "Docs": ["Alien Worlds"]})
    _seed(db, "Jellyfin", {"Films": ["Aliens"]}, MediaServerType.JELLYFIN)

    results = SearchService(db).search_items(GlobalItemSearch(search="alien", page=0, page_size=25))

    assert results.total == 3
    assert {hit.item.title for hit in results.hits} == {"Alien", "Alien Worlds", "Aliens"}

def test_the_page_is_sorted_across_servers_not_concatenated_per_library(db):
    _seed(db, "Plex", {"Movies": ["Alien 3", "Alien Covenant"]})
    _seed(db, "Jellyfin", {"Films": ["Alien Resurrection", "Aliens"]}, MediaServerType.JELLYFIN)

    results = SearchService(db).search_items(GlobalItemSearch(search="alien", page=0, page_size=25))

    assert [hit.item.title for hit in results.hits] == [
        "Alien 3", "Alien Covenant", "Alien Resurrection", "Aliens",
    ]

def test_every_hit_carries_the_server_it_belongs_to(db):
    _seed(db, "Plex", {"Movies": ["Alien"]})
    _seed(db, "Jellyfin", {"Films": ["Aliens"]}, MediaServerType.JELLYFIN)

    hits = {hit.item.title: hit.scope
            for hit in SearchService(db).search_items(GlobalItemSearch(search="alien", page=0, page_size=25)).hits}

    assert (hits["Alien"].media_server_name, hits["Alien"].library_name) == ("Plex", "Movies")
    assert hits["Aliens"].media_server_type == "JELLYFIN"
    assert hits["Alien"].library_id != hits["Aliens"].library_id

def test_a_term_that_matches_nothing_is_an_empty_page_not_the_whole_install(db):
    _seed(db, "Plex", {"Movies": ["Alien", "Dune"]})

    results = SearchService(db).search_items(GlobalItemSearch(search="zzz", page=0, page_size=25))

    assert (results.hits, results.total) == ([], 0)

def test_the_total_counts_the_whole_match_not_the_page(db):
    _seed(db, "Plex", {"Movies": ["Alien", "Aliens", "Alien 3"]})

    results = SearchService(db).search_items(GlobalItemSearch(search="alien", page=0, page_size=2))

    assert len(results.hits) == 2
    assert results.total == 3

def test_a_later_page_continues_the_same_ordering(db):
    _seed(db, "Plex", {"Movies": ["Alien", "Aliens"]})
    _seed(db, "Jellyfin", {"Films": ["Alien 3"]}, MediaServerType.JELLYFIN)

    service = SearchService(db)
    first = service.search_items(GlobalItemSearch(search="alien", page=0, page_size=2))
    second = service.search_items(GlobalItemSearch(search="alien", page=1, page_size=2))

    assert [hit.item.title for hit in first.hits] == ["Alien", "Alien 3"]
    assert [hit.item.title for hit in second.hits] == ["Aliens"]

def test_the_endpoint_returns_hits_with_their_library_and_server(authenticated_app):
    with TestClient(authenticated_app) as client:
        session = SessionLocal()
        try:
            _seed(session, "Plex", {"Movies": ["Zyxwv Quorra"]})
        finally:
            session.close()

        resp = client.get("/affiche/search/items", params={"search": "zyxwv"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["total_pages"] == 1
    hit = body["items"][0]
    assert hit["title"] == "Zyxwv Quorra"
    assert (hit["library_name"], hit["media_server_name"]) == ("Movies", "Plex")
    assert isinstance(hit["media_server_id"], int)

def test_the_endpoint_rejects_an_empty_term(authenticated_app):
    with TestClient(authenticated_app) as client:
        assert client.get("/affiche/search/items", params={"search": ""}).status_code == 422
        assert client.get("/affiche/search/items").status_code == 422

def test_the_endpoint_is_session_gated():
    with TestClient(main_module.app) as client:
        assert client.get("/affiche/search/items", params={"search": "a"}).status_code == 401
