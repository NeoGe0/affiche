from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.model.text_options import TextOptions
from affiche.app.image.poster_decorator_service import PosterDecorationService
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.media_server_poster_service import (
    LibraryPosterService,
    StoredPoster,
)
from affiche.app.mediaserver.service.poster_resetter import PosterResetter
from affiche.config import Base

@pytest.fixture
def db_with_items():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    def build(style_hashes: list):
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
        session.flush()
        LibraryService(session).create(Library(
            media_server_id=server.id, external_id="lib-1", name="Movies",
            type="movie", language="en", enabled=True))
        session.commit()
        library_id = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server.id))[0].id

        service = LibraryService(session)
        service.create_or_update_items_batch([
            LibraryItem(library_id=library_id, external_id=f"e{i}", type="movie", title=f"T{i}")
            for i in range(len(style_hashes))
        ])
        repo = LibraryRepository(session)
        stored = sorted(service.find_items(LibraryItemSearch(library_id=library_id)),
                        key=lambda item: item.external_id)
        for item, style_hash in zip(stored, style_hashes):
            item.processed = True
            item.style_hash = style_hash
            repo.create_or_update_item(item)
        session.commit()
        return repo, LibraryItemSearch(library_id=library_id, processed=True)

    yield build
    session.close()
    engine.dispose()

@pytest.fixture
def decorator() -> PosterDecorationService:
    return PosterDecorationService(
        options=OverlayOptions(border_px=10),
        text_options=TextOptions(all_caps=False),
        generator=MagicMock(),
        composer=MagicMock(),
        text_renderer=MagicMock(),
    )

def test_defaults_and_an_equal_override_agree(decorator):
    assert decorator.style_fingerprint() == decorator.style_fingerprint(
        OverlayOptions(border_px=10), TextOptions(all_caps=False))

def test_a_different_overlay_changes_the_fingerprint(decorator):
    assert decorator.style_fingerprint(OverlayOptions(border_px=42)) != decorator.style_fingerprint()

def test_a_different_text_option_changes_the_fingerprint(decorator):
    before = decorator.style_fingerprint()

    assert decorator.style_fingerprint(text_options=TextOptions(all_caps=True)) != before

def test_editing_the_global_style_restyles_the_libraries_that_inherit_it():
    def build(border_px: int) -> PosterDecorationService:
        return PosterDecorationService(options=OverlayOptions(border_px=border_px),
                                       text_options=TextOptions(),
                                       generator=MagicMock(), composer=MagicMock(),
                                       text_renderer=MagicMock())

    assert build(10).style_fingerprint() != build(11).style_fingerprint()

def test_an_unstyled_poster_has_its_own_constant_fingerprint(decorator):
    unstyled = decorator.style_fingerprint(OverlayOptions(border_px=42), apply_style=False)

    assert unstyled == decorator.style_fingerprint(apply_style=False)
    assert unstyled != decorator.style_fingerprint()

def test_unknown_styles_count_towards_the_total_but_never_as_stale(db_with_items):
    repo, search = db_with_items(["current", None, "older"])

    stale, total = repo.count_style_staleness(search, "current")

    assert (stale, total) == (1, 3)

def test_nothing_is_stale_when_every_poster_matches(db_with_items):
    repo, search = db_with_items(["current", "current"])

    assert repo.count_style_staleness(search, "current") == (0, 2)

def _poster_service(decorator) -> "LibraryPosterService":
    svc = object.__new__(LibraryPosterService)
    svc._decorator = decorator
    svc._uploader = MagicMock()
    svc._save_item_poster = MagicMock(return_value=StoredPoster("p.jpg", "digest"))
    return svc

def test_storing_an_item_poster_records_the_style_it_was_drawn_with(decorator):
    svc = _poster_service(decorator)
    item = LibraryItem(id=1, library_id=10, external_id="x", title="T", type="movie")
    overlay = OverlayOptions(border_px=42)

    svc._process_item_poster(MagicMock(), MagicMock(), item, "http://p.jpg", MagicMock(), upload=False,
                             overlay_options=overlay)

    assert item.style_hash == decorator.style_fingerprint(overlay, None)

def test_an_unstyled_item_poster_is_recorded_as_unstyled(decorator):
    svc = _poster_service(decorator)
    item = LibraryItem(id=1, library_id=10, external_id="x", title="T", type="movie")

    svc._process_item_poster(MagicMock(), MagicMock(), item, "http://p.jpg", MagicMock(), upload=False,
                             apply_style=False)

    assert item.style_hash == PosterDecorationService.UNSTYLED_FINGERPRINT

def test_a_reset_clears_the_style_hash():
    item = LibraryItem(id=1, library_id=10, external_id="x", title="T", type="movie",
                       processed=True, style_hash="old")
    resetter = object.__new__(PosterResetter)
    resetter._delete_poster = MagicMock()
    resetter._cache_source_poster = MagicMock()
    connector = MagicMock()
    connector.reset_poster.return_value = MagicMock(success=True, poster_url="http://s.jpg")

    resetter.reset_poster(MagicMock(), item, connector)

    assert item.style_hash is None
