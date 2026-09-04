import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module
from affiche.app.dashboard import DashboardService
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.collections.connector.library_collection_entity import (
    LibraryCollectionEntity,
)
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.seasons.connector.library_season_entity import (
    LibrarySeasonEntity,
)
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
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

def _seed(session, server_name: str, libraries: dict[str, list[dict]]) -> None:
    server = MediaServerPersistenceConnector(session).create(MediaServer(
        name=server_name, type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    session.flush()
    service = LibraryService(session)
    repo = LibraryRepository(session)

    for index, (library_name, items) in enumerate(libraries.items()):
        service.create(Library(media_server_id=server.id, external_id=f"{server_name}-{index}",
                               name=library_name, type="movie", language="en",
                               enabled=True))
        session.commit()
        library = next(lib for lib in service.find_libraries(LibrarySearch(media_server_id=server.id)) if lib.name == library_name)

        service.create_or_update_items_batch([
            LibraryItem(library_id=library.id, external_id=f"{library.id}-{i}",
                        title=item["title"], type="movie")
            for i, item in enumerate(items)
        ])
        session.commit()

        stored = {item.title: item
                  for item in service.find_items(LibraryItemSearch(library_id=library.id))}
        for item in items:
            entity = stored[item["title"]]
            entity.processed = item.get("processed", False)
            entity.locked = item.get("locked", False)
            entity.error_message = item.get("error_message")
            entity.poster_provider = item.get("poster_provider")
            repo.create_or_update_item(entity)
        session.commit()

def test_an_empty_install_reports_zeroes_rather_than_failing(db):
    summary = DashboardService(db).get_summary()

    assert (summary.library_count, summary.media_server_count) == (0, 0)
    assert summary.totals.total == 0
    assert summary.libraries == []

def test_each_library_reports_its_own_buckets(db):
    _seed(db, "Plex", {
        "Movies": [
            {"title": "Alien", "processed": True, "poster_provider": "tmdb"},
            {"title": "Aliens", "error_message": "boom"},
            {"title": "Blade Runner", "locked": True, "processed": True,
             "poster_provider": "tmdb"},
            {"title": "Dune"},
        ],
        "Docs": [{"title": "Koyaanisqatsi"}],
    })

    rows = {row.library_name: row.stats for row in DashboardService(db).get_summary().libraries}

    assert (rows["Movies"].total, rows["Movies"].processed) == (4, 2)
    assert (rows["Movies"].errors, rows["Movies"].locked) == (1, 1)
    assert rows["Movies"].unprocessed == 1
    assert (rows["Docs"].total, rows["Docs"].unprocessed) == (1, 1)

def test_a_library_with_no_items_still_gets_a_row(db):
    _seed(db, "Plex", {"Movies": []})

    summary = DashboardService(db).get_summary()

    assert [row.library_name for row in summary.libraries] == ["Movies"]
    assert summary.libraries[0].stats.total == 0

def test_the_totals_are_the_sum_of_the_rows(db):
    _seed(db, "Plex", {"Movies": [{"title": "Alien", "processed": True}]})
    _seed(db, "Jellyfin", {"Shows": [{"title": "Twin Peaks", "error_message": "boom"}]})

    summary = DashboardService(db).get_summary()

    assert (summary.media_server_count, summary.library_count) == (2, 2)
    for field in ("total", "processed", "unprocessed", "errors", "locked", "uploaded"):
        assert getattr(summary.totals, field) == sum(
            getattr(row.stats, field) for row in summary.libraries)

def test_providers_are_ranked_by_how_many_posters_they_produced(db):
    _seed(db, "Plex", {"Movies": [
        {"title": "A", "processed": True, "poster_provider": "server"},
        {"title": "B", "processed": True, "poster_provider": "tmdb"},
        {"title": "C", "processed": True, "poster_provider": "tmdb"},
        {"title": "D"},
    ]})

    providers = DashboardService(db).get_summary().providers

    assert [(p.provider, p.count) for p in providers] == [("tmdb", 2), ("server", 1)]

def test_season_and_collection_posters_count_towards_the_breakdown(db):
    _seed(db, "Plex", {"Shows": [{"title": "Twin Peaks", "processed": True,
                                  "poster_provider": "tmdb"}]})
    library_id = LibraryService(db).find_libraries(LibrarySearch(
        media_server_id=MediaServerPersistenceConnector(db).find_all()[0].id))[0].id
    show = LibraryService(db).find_items(LibraryItemSearch(library_id=library_id))[0]
    db.add_all([
        LibrarySeasonEntity(show_id=show.id, library_id=library_id, external_id="s1",
                            season_number=1, title="Season 1", poster_provider="mediux"),
        LibrarySeasonEntity(show_id=show.id, library_id=library_id, external_id="s2",
                            season_number=2, title="Season 2", poster_provider="mediux"),
        LibraryCollectionEntity(external_id="c1", library_id=library_id, title="Saga",
                                poster_provider="fanart"),
    ])
    db.commit()

    providers = DashboardService(db).get_summary().providers

    assert [(p.provider, p.count) for p in providers] == [
        ("mediux", 2), ("fanart", 1), ("tmdb", 1)]

def test_the_endpoint_answers_with_the_summary_and_recent_tasks(authenticated_app):
    with TestClient(authenticated_app) as client:
        session = SessionLocal()
        try:
            _seed(session, "Plex", {"Movies": [{"title": "Alien", "processed": True,
                                                "poster_provider": "tmdb"}]})
        finally:
            session.close()

        resp = client.get("/affiche/dashboard")

    assert resp.status_code == 200
    body = resp.json()
    assert body["totals"]["total"] == 1
    assert body["library_count"] == 1
    assert body["libraries"][0]["media_server_name"] == "Plex"
    assert body["providers"] == [{"provider": "tmdb", "count": 1}]
    assert isinstance(body["recent_tasks"], list)

def test_the_endpoint_is_session_gated():
    with TestClient(main_module.app) as client:
        assert client.get("/affiche/dashboard").status_code == 401
