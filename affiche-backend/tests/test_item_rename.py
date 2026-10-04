import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.service.item_rename_service import (
    ALREADY_CORRECT,
    ItemRenameError,
    ItemRenameService,
    NO_ID,
    NOT_CONFIGURED,
    NOT_FOUND,
)
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config import Base
from affiche.config.exceptions.exceptions import (LibraryItemNotFoundException,
                                                 LibraryNotFoundException)
from affiche.external.poster.poster_service import TitleMatch

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
                           type="movie", language="fr-FR", enabled=True))
    db.commit()
    stored_library = service.find_libraries(LibrarySearch(media_server_id=server.id))[0]

    service.create_or_update_items_batch([
        LibraryItem(library_id=stored_library.id, external_id="100",
                    title="My.movie.2012.1080p", type="movie"),
    ])
    db.commit()
    return server.id, stored_library

def _item(db, library_id: int) -> LibraryItem:
    return LibraryService(db).find_items(LibraryItemSearch(library_id=library_id))[0]

def _service(db, connector: MagicMock, aggregator=None) -> ItemRenameService:
    factory = MagicMock()
    factory.get.return_value = connector
    return ItemRenameService(db, connector_factory=factory, poster_aggregator=aggregator)

def _connector(rename_item=True) -> MagicMock:
    connector = MagicMock()
    connector.rename_item.return_value = rename_item
    return connector

def test_renaming_writes_to_the_media_server_then_records_the_row(db, library):
    server_id, lib = library
    connector = _connector()

    renamed = _service(db, connector).rename_item(server_id, lib.id, _item(db, lib.id).id,
                                                  "My Movie")

    connector.rename_item.assert_called_once_with("100", "My Movie")
    assert renamed.title == "My Movie"
    assert _item(db, lib.id).title == "My Movie"

def test_a_server_that_refuses_leaves_our_row_alone(db, library):
    server_id, lib = library

    with pytest.raises(ItemRenameError):
        _service(db, _connector(rename_item=False)).rename_item(
            server_id, lib.id, _item(db, lib.id).id, "My Movie")

    assert _item(db, lib.id).title == "My.movie.2012.1080p"

def test_the_title_is_trimmed_and_the_unchanged_case_costs_no_upstream_call(db, library):
    server_id, lib = library
    connector = _connector()
    service = _service(db, connector)
    item_id = _item(db, lib.id).id

    service.rename_item(server_id, lib.id, item_id, "  My Movie  ")
    assert _item(db, lib.id).title == "My Movie"

    service.rename_item(server_id, lib.id, item_id, "My Movie")
    connector.rename_item.assert_called_once()

@pytest.mark.parametrize("title", ["", "   "])
def test_a_blank_title_is_refused_before_the_server_is_asked(db, library, title):
    server_id, lib = library
    connector = _connector()

    with pytest.raises(ItemRenameError):
        _service(db, connector).rename_item(server_id, lib.id, _item(db, lib.id).id, title)

    connector.rename_item.assert_not_called()

def test_a_title_longer_than_the_column_is_refused(db, library):
    server_id, lib = library
    connector = _connector()

    with pytest.raises(ItemRenameError):
        _service(db, connector).rename_item(server_id, lib.id, _item(db, lib.id).id, "x" * 1025)

    connector.rename_item.assert_not_called()

def test_a_service_with_no_connector_refuses_rather_than_writing_locally(db, library):
    server_id, lib = library

    with pytest.raises(ItemRenameError):
        ItemRenameService(db).rename_item(server_id, lib.id, _item(db, lib.id).id, "My Movie")

    assert _item(db, lib.id).title == "My.movie.2012.1080p"

def test_an_item_in_another_media_servers_library_is_not_reachable(db, library):
    server_id, lib = library
    other = MediaServerPersistenceConnector(db).create(MediaServer(
        name="Other", type=MediaServerType.PLEX, url="http://y", token="t2"))
    db.commit()
    connector = _connector()

    with pytest.raises(LibraryNotFoundException):
        _service(db, connector).rename_item(other.id, lib.id, _item(db, lib.id).id, "My Movie")

    connector.rename_item.assert_not_called()

def test_a_missing_item_is_not_found_rather_than_renamed(db, library):
    server_id, lib = library
    connector = _connector()

    with pytest.raises(LibraryItemNotFoundException):
        _service(db, connector).rename_item(server_id, lib.id, 9999, "My Movie")

    connector.rename_item.assert_not_called()

def _aggregator(matched=None) -> MagicMock:
    aggregator = MagicMock()
    aggregator.title_from_ids.return_value = matched
    return aggregator

def _identify(db, library_id: int, **ids) -> LibraryItem:
    item = _item(db, library_id)
    for field, value in ids.items():
        setattr(item, field, value)
    stored = LibraryService(db).library_repo.create_or_update_item(item)
    db.commit()
    return stored

def test_the_title_comes_from_the_id_and_is_labelled_with_who_gave_it(db, library):
    server_id, lib = library
    item = _identify(db, lib.id, tmdb_id=603)
    aggregator = _aggregator(TitleMatch(title="The Matrix", provider="tmdb"))

    suggestions = _service(db, _connector(), aggregator).suggest_titles(server_id, lib.id, item.id)

    assert suggestions.current == "My.movie.2012.1080p"
    assert (suggestions.matched.title, suggestions.matched.provider) == ("The Matrix", "tmdb")

def test_the_language_asked_for_is_the_librarys_own(db, library):
    server_id, lib = library
    item = _identify(db, lib.id, tmdb_id=603)
    aggregator = _aggregator(TitleMatch(title="Matrix", provider="tmdb"))

    _service(db, _connector(), aggregator).suggest_titles(server_id, lib.id, item.id)

    aggregator.title_from_ids.assert_called_once_with(
        media_type="movie", language="fr", tmdb_id=603, tvdb_id=None)

def test_an_item_with_no_id_gets_nothing_rather_than_a_guess(db, library):
    server_id, lib = library
    aggregator = _aggregator(matched=None)

    suggestions = _service(db, _connector(), aggregator).suggest_titles(
        server_id, lib.id, _item(db, lib.id).id)

    assert suggestions.matched is None
    assert suggestions.reason == NO_ID
    assert suggestions.current == "My.movie.2012.1080p"
    aggregator.title_from_ids.assert_not_called()

def test_an_imdb_id_alone_is_not_usable(db, library):
    server_id, lib = library
    item = _identify(db, lib.id, imdb_id="tt0133093")
    aggregator = _aggregator(TitleMatch(title="The Matrix", provider="tmdb"))

    _service(db, _connector(), aggregator).suggest_titles(server_id, lib.id, item.id)

    aggregator.title_from_ids.assert_not_called()

def test_an_id_no_catalogue_recognises_says_so_rather_than_blaming_the_id(db, library):
    server_id, lib = library
    item = _identify(db, lib.id, tmdb_id=999999)

    suggestions = _service(db, _connector(), _aggregator(None)).suggest_titles(
        server_id, lib.id, item.id)

    assert (suggestions.matched, suggestions.reason) == (None, NOT_FOUND)

def test_a_catalogue_that_agrees_reports_agreement_not_a_missing_id(db, library):
    server_id, lib = library
    item = _identify(db, lib.id, tmdb_id=603)
    aggregator = _aggregator(TitleMatch(title=item.title, provider="tmdb"))

    suggestions = _service(db, _connector(), aggregator).suggest_titles(server_id, lib.id, item.id)

    assert (suggestions.matched, suggestions.reason) == (None, ALREADY_CORRECT)

def test_suggestions_still_answer_when_no_provider_is_configured(db, library):
    server_id, lib = library
    item = _identify(db, lib.id, tmdb_id=603)

    suggestions = ItemRenameService(db).suggest_titles(server_id, lib.id, item.id)

    assert (suggestions.matched, suggestions.reason) == (None, NOT_CONFIGURED)
    assert suggestions.current == "My.movie.2012.1080p"

def test_plex_locks_the_title_it_writes():
    from affiche.external.plex.service.plex_service import PlexService

    service = PlexService("http://plex", "token")
    item = MagicMock()
    service._plex = MagicMock()
    service._plex.fetchItem.return_value = item

    assert service.rename_item("100", "My Movie") is True
    item.editTitle.assert_called_once_with("My Movie")

def test_plex_reports_a_failure_rather_than_raising():
    from affiche.external.plex.service.plex_service import PlexService

    service = PlexService("http://plex", "token")
    service._plex = MagicMock()
    service._plex.fetchItem.side_effect = Exception("gone")

    assert service.rename_item("100", "My Movie") is False

def test_jellyfin_adds_name_to_the_locked_fields_it_read_back():
    from affiche.external.jellyfin.service.jellyfin_service import JellyfinService

    service = JellyfinService("http://jellyfin", "key")
    service._get = MagicMock(return_value={'Items': [{'Id': 'abc', 'Name': 'My.movie.2012.1080p',
                                                      'LockedFields': ['Overview']}]})
    service._post = MagicMock()

    assert service.rename_item("abc", "My Movie") is True
    payload = json.loads(service._post.call_args.kwargs['data'])
    assert payload['Name'] == "My Movie"
    assert payload['LockedFields'] == ['Overview', 'Name']

def test_jellyfin_reports_a_failure_when_the_item_is_gone():
    from affiche.external.jellyfin.service.jellyfin_service import JellyfinService

    service = JellyfinService("http://jellyfin", "key")
    service._get = MagicMock(return_value={'Items': []})
    service._post = MagicMock()

    assert service.rename_item("abc", "My Movie") is False
    service._post.assert_not_called()

def test_the_rename_endpoints_are_session_gated():
    with TestClient(main_module.app) as client:
        base = "/affiche/media-servers/1/libraries/1/items/1"
        assert client.patch(base, json={"title": "X"}).status_code == 401
        assert client.get(f"{base}/title/suggestions").status_code == 401

@pytest.mark.parametrize("title", ["", "   ", "x" * 1025])
def test_the_rename_endpoint_rejects_a_title_the_column_cannot_hold(authenticated_app, title):
    with TestClient(authenticated_app) as client:
        response = client.patch("/affiche/media-servers/1/libraries/1/items/1",
                                json={"title": title})
        assert response.status_code == 422
