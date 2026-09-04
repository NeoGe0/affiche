from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import (
    NO_PROVIDER, ItemStatusFilter, Library, LibraryItem, LibraryItemSearch,
    LibrarySearch,
)
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.poster_resolver import (
    SERVER_PROVIDER,
    PosterResolver,
    ServerPosterSettings,
)
from affiche.config import Base
from affiche.config.language_config import TEXTLESS
from affiche.external.poster.poster_service import ProviderPoster

SERVER_URL = "http://plex.local/library/metadata/9/thumb"

def _settings(fallback=False) -> ServerPosterSettings:
    return ServerPosterSettings(language_order=[TEXTLESS, "en"],
                                fallback_to_server_poster=fallback,
                                skip_style_when_not_textless=False)

def _item(**overrides) -> LibraryItem:
    fields = dict(id=42, library_id=1, external_id="x", title="T", type="movie", tmdb_id=7,
                  poster_url=SERVER_URL, processed=False, poster_hash=None)
    fields.update(overrides)
    return LibraryItem(**fields)

def _file_store(has_local_copy: bool = False) -> MagicMock:
    store = MagicMock()
    store.exists.return_value = has_local_copy
    store.path.return_value = "/filestore/1/42.jpg"
    return store

def test_the_resolver_reports_which_provider_answered():
    aggregator = MagicMock()
    aggregator.find_best_poster.side_effect = [None, ProviderPoster("http://tvdb/p.jpg", "tvdb")]

    poster = PosterResolver(aggregator, _file_store()).resolve_item_poster(
        _item(), "movie", ["tmdb", "tvdb"], _settings())

    assert (poster.source, poster.provider) == ("http://tvdb/p.jpg", "tvdb")

def test_a_season_poster_reports_its_provider_too():
    aggregator = MagicMock()
    aggregator.find_best_season_poster.return_value = ProviderPoster("http://s1.jpg", "fanart")
    season = LibrarySeason(id=9, show_id=42, library_id=1, external_id="s", season_number=1,
                           title="Season 1")

    poster = PosterResolver(aggregator, _file_store()).resolve_season_poster(
        _item(type="show"), season, ["fanart"], _settings())

    assert poster.provider == "fanart"

def test_the_server_fallback_is_named_rather_than_left_blank():
    aggregator = MagicMock()
    aggregator.find_best_poster.return_value = None

    poster = PosterResolver(aggregator, _file_store()).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings(fallback=True))

    assert poster.provider == SERVER_PROVIDER

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
def library_id(db) -> int:
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    db.flush()
    LibraryService(db).create(Library(
        media_server_id=server.id, external_id="lib-1", name="Movies",
        type="movie", language="en", enabled=True,
    ))
    db.commit()
    return LibraryService(db).find_libraries(LibrarySearch(media_server_id=server.id))[0].id

def _seed(db, library_id: int, titles: list[str]) -> dict[str, LibraryItem]:
    LibraryService(db).create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id=f"e{i}", title=title, type="movie")
        for i, title in enumerate(titles)
    ])
    db.commit()
    return {item.title: item
            for item in LibraryService(db).find_items(LibraryItemSearch(library_id=library_id))}

def _set_provider(db, item: LibraryItem, provider) -> None:
    item.poster_provider = provider
    item.processed = provider is not None
    LibraryRepository(db).create_or_update_item(item)
    db.commit()

def test_a_new_item_has_no_recorded_provider(db, library_id):
    assert _seed(db, library_id, ["Alien"])["Alien"].poster_provider is None

def test_a_sync_does_not_overwrite_the_recorded_provider(db, library_id):
    items = _seed(db, library_id, ["Alien"])
    _set_provider(db, items["Alien"], "shoko")

    _seed(db, library_id, ["Alien"])

    assert LibraryService(db).find_items(
        LibraryItemSearch(library_id=library_id))[0].poster_provider == "shoko"

def test_the_provider_breakdown_counts_each_provider(db, library_id):
    items = _seed(db, library_id, ["A", "B", "C", "D"])
    _set_provider(db, items["A"], "tmdb")
    _set_provider(db, items["B"], "tmdb")
    _set_provider(db, items["C"], SERVER_PROVIDER)

    counts = LibraryService(db).count_items_by_provider(LibraryItemSearch(library_id=library_id))

    assert counts == {"tmdb": 2, SERVER_PROVIDER: 1, None: 1}

def test_clearing_the_provider_moves_the_item_to_the_no_provenance_bucket(db, library_id):
    items = _seed(db, library_id, ["Alien"])
    _set_provider(db, items["Alien"], "tmdb")
    _set_provider(db, items["Alien"], None)

    assert LibraryService(db).count_items_by_provider(LibraryItemSearch(library_id=library_id)) == {None: 1}

def test_the_provider_filter_selects_only_that_provider(db, library_id):
    items = _seed(db, library_id, ["A", "B", "C"])
    _set_provider(db, items["A"], "tmdb")
    _set_provider(db, items["B"], "mediux")

    found = LibraryService(db).find_items(
        LibraryItemSearch(library_id=library_id, provider="mediux"))

    assert [item.title for item in found] == ["B"]

def test_the_no_provider_sentinel_selects_the_items_with_no_provenance(db, library_id):
    items = _seed(db, library_id, ["A", "B"])
    _set_provider(db, items["A"], "tmdb")

    found = LibraryService(db).find_items(
        LibraryItemSearch(library_id=library_id, provider=NO_PROVIDER))

    assert [item.title for item in found] == ["B"]

def test_the_provider_filter_combines_with_a_status_filter(db, library_id):
    items = _seed(db, library_id, ["A", "B", "C"])
    _set_provider(db, items["A"], "tmdb")
    _set_provider(db, items["B"], "tmdb")
    items["B"].locked = True
    LibraryRepository(db).create_or_update_item(items["B"])
    db.commit()

    found = LibraryService(db).find_items(LibraryItemSearch(
        library_id=library_id, provider="tmdb", status=ItemStatusFilter.LOCKED))

    assert [item.title for item in found] == ["B"]
