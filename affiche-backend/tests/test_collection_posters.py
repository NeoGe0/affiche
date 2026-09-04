from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import affiche.main as main_module  # noqa: F401  (initialises DI before the imports below)
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.collections.connector.library_collection_entity import (
    LibraryCollectionEntity,
)
from affiche.app.mediaserver.library.collections.library_collection_repository import (
    LibraryCollectionRepository,
)
from affiche.app.mediaserver.library.collections.model.library_collection import (
    LibraryCollection,
    LibraryCollectionSearch,
)
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service import collection_poster_service as module
from affiche.app.mediaserver.service.collection_poster_service import CollectionPosterService
from affiche.external.poster.poster_service import ProviderPoster
from affiche.app.mediaserver.service.library_style import GLOBAL_STYLE, LibraryPosterStyle
from affiche.config import Base
from affiche.config.database import SessionLocal
from affiche.config.dependencies import container

MEDIA_SERVER_ID = 1
JPEG = b"\xff\xd8\xff\xe0decorated"

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session, factory
    session.close()
    engine.dispose()

@pytest.fixture
def store(tmp_path):
    return FileStoreService(root_dir=str(tmp_path), kind="collections")

@pytest.fixture
def decorator():
    return MagicMock(decorate_poster=MagicMock(return_value=JPEG))

def _library(session, track_collections=True, upload_enabled=True) -> int:
    server = MediaServerPersistenceConnector(session).create(MediaServer(
        name="Plex", type=MediaServerType.PLEX, url="http://x", token="t"))
    session.flush()
    service = LibraryService(session)
    service.create(Library(media_server_id=server.id, external_id="1", name="Movies",
                           type="movie", language="en", enabled=True))
    session.commit()
    library = service.find_libraries(LibrarySearch(media_server_id=server.id))[0]
    LibrarySettingsService(session).partial_update_settings(
        library.id, {"track_collections": track_collections, "upload_enabled": upload_enabled})
    session.commit()
    return library.id

def _collection(session, library_id, title="Trilogy", poster_url="http://server/art.jpg",
                processed=False, locked=False,
                tmdb_collection_id=None) -> LibraryCollection:
    repo = LibraryCollectionRepository(session)
    repo.create_or_update_batch([LibraryCollection(
        library_id=library_id, external_id=title.lower(), title=title, poster_url=poster_url)])
    session.commit()

    stored = next(c for c in repo.find_collections(LibraryCollectionSearch(library_id=library_id))
                  if c.title == title)
    entity = session.get(LibraryCollectionEntity, stored.id)
    entity.processed = processed
    entity.locked = locked
    entity.tmdb_collection_id = tmdb_collection_id
    session.commit()
    return repo.get_collection(library_id, stored.id)

@pytest.fixture
def service(db, store, decorator):
    _, factory = db
    return CollectionPosterService(session_factory=factory, file_store=store, decorator=decorator)

class TestSourceDownload:

    def test_a_collections_server_artwork_lands_in_the_store(self, db, store, service, monkeypatch):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        monkeypatch.setattr(module, "fetch_as_jpeg", lambda url: b"server-art")

        assert service.download_source_posters(MEDIA_SERVER_ID, library_id) == 1
        assert store.fetch(library_id, collection.id) == b"server-art"

    def test_a_collection_with_no_server_artwork_is_skipped(self, db, service, monkeypatch):
        session, _ = db
        library_id = _library(session)
        _collection(session, library_id, poster_url=None)
        monkeypatch.setattr(module, "fetch_as_jpeg", lambda url: b"server-art")

        assert service.download_source_posters(MEDIA_SERVER_ID, library_id) == 0

    def test_a_stored_poster_is_never_re_downloaded(self, db, store, service, monkeypatch):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"already-here")
        monkeypatch.setattr(module, "fetch_as_jpeg", lambda url: b"server-art")

        assert service.download_source_posters(MEDIA_SERVER_ID, library_id) == 0
        assert store.fetch(library_id, collection.id) == b"already-here"

    def test_a_processed_collection_is_left_alone(self, db, service, monkeypatch):
        session, _ = db
        library_id = _library(session)
        _collection(session, library_id, processed=True)
        monkeypatch.setattr(module, "fetch_as_jpeg", lambda url: b"server-art")

        assert service.download_source_posters(MEDIA_SERVER_ID, library_id) == 0

    def test_nothing_happens_when_the_library_does_not_track_collections(self, db, service,
                                                                        monkeypatch):
        session, _ = db
        library_id = _library(session, track_collections=False)
        _collection(session, library_id)
        monkeypatch.setattr(module, "fetch_as_jpeg", lambda url: b"server-art")

        assert service.download_source_posters(MEDIA_SERVER_ID, library_id) == 0

    def test_one_unreachable_image_does_not_abandon_the_rest(self, db, store, service, monkeypatch):
        session, _ = db
        library_id = _library(session)
        _collection(session, library_id, title="Broken", poster_url="http://server/broken.jpg")
        good = _collection(session, library_id, title="Fine")

        def fetch(url):
            if "broken" in url:
                raise OSError("404")
            return b"server-art"

        monkeypatch.setattr(module, "fetch_as_jpeg", fetch)

        assert service.download_source_posters(MEDIA_SERVER_ID, library_id) == 1
        assert store.exists(library_id, good.id)

class TestGeneration:

    def test_the_stored_artwork_is_decorated_with_the_collection_title(self, db, store, service,
                                                                      decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert store.fetch(library_id, collection.id) == JPEG
        assert decorator.decorate_poster.call_args.args[1] == "Trilogy"

    def test_generating_marks_the_collection_processed(self, db, store, service):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        stored = LibraryCollectionRepository(session).get_collection(library_id, collection.id)
        assert stored.processed is True

    def test_the_server_artwork_is_preserved_before_it_is_written_over(self, db, store, service):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        assert store.fetch_source(library_id, collection.id) == b"server-art"

    def test_a_regeneration_draws_on_the_source_not_on_the_last_poster(self, db, store, service,
                                                                      decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")
        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        assert decorator.decorate_poster.call_args.args[0] == b"server-art"

    def test_a_locked_collection_is_skipped(self, db, store, service):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, locked=True)
        store.save(library_id, collection.id, b"server-art")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 0
        assert store.fetch(library_id, collection.id) == b"server-art"

    def test_a_collection_with_nothing_to_draw_on_is_skipped(self, db, service):
        session, _ = db
        library_id = _library(session)
        _collection(session, library_id, poster_url=None)

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 0

    def test_the_server_url_is_used_when_nothing_is_stored_yet(self, db, service, decorator):
        session, _ = db
        library_id = _library(session)
        _collection(session, library_id, poster_url="http://server/art.jpg")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert decorator.decorate_poster.call_args.args[0] == "http://server/art.jpg"

    def test_the_library_style_reaches_the_decorator(self, db, store, service, decorator,
                                                     monkeypatch):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")
        style = LibraryPosterStyle(overlay_options="OVERLAY", text_options="TEXT")
        monkeypatch.setattr(module, "resolve_library_style", lambda _s, _l: style)

        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        assert decorator.decorate_poster.call_args.kwargs["overlay_options"] == "OVERLAY"
        assert decorator.decorate_poster.call_args.kwargs["text_options"] == "TEXT"

    def test_a_library_that_does_not_track_collections_generates_nothing(self, db, store, service):
        session, _ = db
        library_id = _library(session, track_collections=False)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 0

    def test_a_decorator_failure_leaves_the_collection_unprocessed(self, db, store, service,
                                                                   decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")
        decorator.decorate_poster.side_effect = RuntimeError("bad image")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 0
        stored = LibraryCollectionRepository(session).get_collection(library_id, collection.id)
        assert stored.processed is False

    def test_a_generated_poster_is_counted_against_the_server_provider(self, db, store, service):
        from affiche.app.provider_stats import ProviderStatsQuery, ProviderStatsService

        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        assert ProviderStatsService(session).totals(ProviderStatsQuery()).get("server") == 1

def test_the_style_resolution_is_the_one_items_use(db):
    session, _ = db
    library_id = _library(session)

    from affiche.app.mediaserver.service.library_style import resolve_library_style

    assert resolve_library_style(session, library_id) == GLOBAL_STYLE

class TestManualPick:

    def test_a_picked_poster_is_decorated_and_stored(self, db, store, service, decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)

        assert service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id,
                                    "http://example/chosen.jpg") is True
        assert store.fetch(library_id, collection.id) == JPEG
        assert decorator.decorate_poster.call_args.args[0] == "http://example/chosen.jpg"

    def test_the_collection_title_is_drawn_unless_one_is_given(self, db, service, decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://example/a.jpg")

        assert decorator.decorate_poster.call_args.args[1] == "Trilogy"

    def test_a_given_title_wins(self, db, service, decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://example/a.jpg",
                             title="The Whole Saga")

        assert decorator.decorate_poster.call_args.args[1] == "The Whole Saga"

    def test_a_picked_poster_marks_the_collection_processed(self, db, service):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://example/a.jpg")

        stored = LibraryCollectionRepository(session).get_collection(library_id, collection.id)
        assert stored.processed is True

    def test_the_server_artwork_is_still_preserved(self, db, store, service):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://example/a.jpg")

        assert store.fetch_source(library_id, collection.id) == b"server-art"

    def test_a_per_call_style_replaces_the_library_one(self, db, service, decorator, monkeypatch):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        monkeypatch.setattr(module, "resolve_library_style",
                            lambda _s, _l: LibraryPosterStyle(overlay_options="LIB",
                                                              text_options="LIB"))

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://example/a.jpg",
                             overlay_options="EDITED")

        assert decorator.decorate_poster.call_args.kwargs["overlay_options"] == "EDITED"
        assert decorator.decorate_poster.call_args.kwargs["text_options"] == "LIB"

    def test_it_falls_back_to_the_library_style(self, db, service, decorator, monkeypatch):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        monkeypatch.setattr(module, "resolve_library_style",
                            lambda _s, _l: LibraryPosterStyle(overlay_options="LIB"))

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://example/a.jpg")

        assert decorator.decorate_poster.call_args.kwargs["overlay_options"] == "LIB"

    def test_a_picked_poster_is_counted_as_manual(self, db, service):
        from affiche.app.provider_stats import ProviderStatsQuery, ProviderStatsService

        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://example/a.jpg")

        assert ProviderStatsService(session).totals(ProviderStatsQuery()).get("manual") == 1

    def test_a_failure_reports_rather_than_pretending(self, db, service, decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        decorator.decorate_poster.side_effect = RuntimeError("not an image")

        assert service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id,
                                    "http://example/a.jpg") is False

    def test_a_locked_collection_can_still_be_picked_by_hand(self, db, store, service):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, locked=True)

        assert service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id,
                                    "http://example/a.jpg") is True
        assert store.fetch(library_id, collection.id) == JPEG

class TestEndpoint:

    @pytest.fixture
    def seeder(self):
        created = []

        def seed():
            session = SessionLocal()
            try:
                library_id = _library(session)
                collection = _collection(session, library_id)
                server_id = session.execute(
                    text("SELECT id FROM media_server")).scalars().all()[-1]
                created.append(server_id)
                return server_id, library_id, collection.id
            finally:
                session.close()

        yield seed

        session = SessionLocal()
        try:
            for server_id in created:
                session.execute(text("DELETE FROM media_server WHERE id = :id"), {"id": server_id})
            session.commit()
        finally:
            session.close()

    def test_applying_a_poster_answers_no_content(self, authenticated_app, monkeypatch, seeder):
        with TestClient(authenticated_app) as client:
            server_id, library_id, collection_id = seeder()
            fake = MagicMock(apply_poster=MagicMock(return_value=True))
            monkeypatch.setattr(container, "collection_poster_service", lambda *a, **k: fake)

            resp = client.post(
                f"/affiche/media-servers/{server_id}/libraries/{library_id}"
                f"/collections/{collection_id}/posters",
                json={"poster_url": "http://example/a.jpg"})

        assert resp.status_code == 204
        assert fake.apply_poster.call_args.args[3] == "http://example/a.jpg"

    def test_a_poster_that_could_not_be_applied_is_a_bad_gateway(self, authenticated_app,
                                                                 monkeypatch, seeder):
        with TestClient(authenticated_app) as client:
            server_id, library_id, collection_id = seeder()
            fake = MagicMock(apply_poster=MagicMock(return_value=False))
            monkeypatch.setattr(container, "collection_poster_service", lambda *a, **k: fake)

            resp = client.post(
                f"/affiche/media-servers/{server_id}/libraries/{library_id}"
                f"/collections/{collection_id}/posters",
                json={"poster_url": "http://example/a.jpg"})

        assert resp.status_code == 502

    def test_an_unknown_collection_is_a_not_found(self, authenticated_app, monkeypatch, seeder):
        with TestClient(authenticated_app) as client:
            server_id, library_id, _ = seeder()
            fake = MagicMock(apply_poster=MagicMock(return_value=True))
            monkeypatch.setattr(container, "collection_poster_service", lambda *a, **k: fake)

            resp = client.post(
                f"/affiche/media-servers/{server_id}/libraries/{library_id}"
                f"/collections/999999/posters",
                json={"poster_url": "http://example/a.jpg"})

        assert resp.status_code == 404
        fake.apply_poster.assert_not_called()

    def test_the_endpoint_is_session_gated(self):
        with TestClient(main_module.app) as client:
            resp = client.post("/affiche/media-servers/1/libraries/1/collections/1/posters",
                               json={"poster_url": "http://example/a.jpg"})
        assert resp.status_code == 401

class TestCatalogue:

    @pytest.fixture
    def aggregator(self):
        return MagicMock(get_all_collection_posters=MagicMock(return_value=[]),
                         find_collection_id=MagicMock(return_value=None))

    @pytest.fixture
    def service(self, db, store, decorator, aggregator):
        _, factory = db
        return CollectionPosterService(session_factory=factory, file_store=store,
                                       decorator=decorator,
                                       aggregator_factory=lambda _session: aggregator)

    def _member(self, session, library_id, collection_id, tmdb_id="8091"):
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library_id, external_id="m1", title="Alien", type="movie",
            tmdb_id=tmdb_id)])
        session.commit()
        item = service.find_items(LibraryItemSearch(library_id=library_id))[0]
        LibraryCollectionRepository(session).set_members(collection_id, [item.id])
        session.commit()
        return item

    def test_a_catalogue_poster_is_preferred_over_the_server_artwork(self, db, store, service,
                                                                     aggregator, decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, tmdb_collection_id=8091)
        store.save(library_id, collection.id, b"server-art")
        aggregator.get_all_collection_posters.return_value = [
            ProviderPoster("http://tmdb/alien.jpg", "tmdb")]

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert decorator.decorate_poster.call_args.args[0] == "http://tmdb/alien.jpg"
        assert aggregator.get_all_collection_posters.call_args.args[0] == 8091

    def test_generation_never_resolves_an_id_itself(self, db, store, service, aggregator,
                                                    decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        self._member(session, library_id, collection.id)
        store.save(library_id, collection.id, b"server-art")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        aggregator.find_collection_id.assert_not_called()
        assert decorator.decorate_poster.call_args.args[0] == b"server-art"

    def test_an_unmatched_collection_asks_the_catalogue_for_nothing(self, db, store, service,
                                                                    aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        aggregator.get_all_collection_posters.assert_not_called()

    def test_a_catalogue_that_answers_nothing_falls_back(self, db, store, service, aggregator,
                                                         decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, tmdb_collection_id=1234)
        store.save(library_id, collection.id, b"server-art")
        aggregator.get_all_collection_posters.return_value = []

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert decorator.decorate_poster.call_args.args[0] == b"server-art"

    def test_a_catalogue_failure_never_fails_the_run(self, db, store, service, aggregator,
                                                     decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, tmdb_collection_id=1234)
        store.save(library_id, collection.id, b"server-art")
        aggregator.get_all_collection_posters.side_effect = RuntimeError("TMDB is down")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert decorator.decorate_poster.call_args.args[0] == b"server-art"

    def test_a_catalogue_poster_is_counted_against_tmdb(self, db, store, service, aggregator):
        from affiche.app.provider_stats import ProviderStatsQuery, ProviderStatsService

        session, _ = db
        library_id = _library(session)
        _collection(session, library_id, tmdb_collection_id=1234)
        aggregator.get_all_collection_posters.return_value = [
            ProviderPoster("http://tmdb/a.jpg", "tmdb")]

        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        assert ProviderStatsService(session).totals(ProviderStatsQuery()).get("tmdb") == 1

    def test_without_an_aggregator_nothing_changes(self, db, store, decorator):
        session, factory = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")
        plain = CollectionPosterService(session_factory=factory, file_store=store,
                                        decorator=decorator)

        assert plain.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert decorator.decorate_poster.call_args.args[0] == b"server-art"

class TestUpload:

    @pytest.fixture
    def connector(self):
        return MagicMock(upload_poster=MagicMock(return_value=True))

    @pytest.fixture
    def service(self, db, store, decorator, connector):
        _, factory = db
        return CollectionPosterService(session_factory=factory, file_store=store,
                                       decorator=decorator,
                                       connector_factory=MagicMock(
                                           get=MagicMock(return_value=connector)))

    @staticmethod
    def _stored(session, library_id, collection_id) -> LibraryCollection:
        return LibraryCollectionRepository(session).get_collection(library_id, collection_id)

    def test_a_generated_poster_is_pushed_to_the_media_server(self, db, store, service, connector):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert connector.upload_poster.call_args.args[0] == collection.external_id

    def test_a_library_with_uploads_off_keeps_its_poster_local(self, db, store, service, connector):
        session, _ = db
        library_id = _library(session, upload_enabled=False)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        connector.upload_poster.assert_not_called()
        assert self._stored(session, library_id, collection.id).poster_uploaded_at is None

    def test_a_successful_push_records_what_the_server_holds(self, db, store, service):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id)

        stored = self._stored(session, library_id, collection.id)
        assert stored.poster_hash == store.digest(library_id, collection.id)
        assert stored.poster_uploaded_at is not None

    def test_a_failed_push_still_leaves_the_poster_generated(self, db, store, service, connector):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")
        connector.upload_poster.return_value = False

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        stored = self._stored(session, library_id, collection.id)
        assert stored.processed is True
        assert stored.poster_uploaded_at is None
        assert stored.poster_hash is None

    def test_an_unreachable_server_never_fails_the_run(self, db, store, service, connector):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")
        connector.upload_poster.side_effect = RuntimeError("no route to host")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert store.fetch(library_id, collection.id) == JPEG

    def test_without_a_connector_factory_generation_is_unchanged(self, db, store, decorator):
        session, factory = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")
        plain = CollectionPosterService(session_factory=factory, file_store=store,
                                        decorator=decorator)

        assert plain.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert self._stored(session, library_id, collection.id).poster_uploaded_at is None

    def test_a_hand_picked_poster_is_pushed_when_the_checkbox_is_on(self, db, service, connector):
        session, _ = db
        library_id = _library(session, upload_enabled=False)
        collection = _collection(session, library_id)

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://x/a.jpg",
                             upload=True)

        assert connector.upload_poster.called

    def test_the_checkbox_can_also_hold_the_poster_back(self, db, service, connector):
        session, _ = db
        library_id = _library(session, upload_enabled=True)
        collection = _collection(session, library_id)

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://x/a.jpg",
                             upload=False)

        connector.upload_poster.assert_not_called()

    def test_an_unstated_choice_follows_the_library(self, db, service, connector):
        session, _ = db
        library_id = _library(session, upload_enabled=True)
        collection = _collection(session, library_id)

        service.apply_poster(MEDIA_SERVER_ID, library_id, collection.id, "http://x/a.jpg")

        assert connector.upload_poster.called

    def test_the_upload_run_pushes_the_stored_posters(self, db, store, service, connector):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, processed=True)
        store.save(library_id, collection.id, JPEG)

        assert service.upload_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert connector.upload_poster.call_args.args[0] == collection.external_id

    def test_the_upload_run_skips_a_poster_the_server_already_holds(self, db, store, service,
                                                                    connector):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, processed=True)
        store.save(library_id, collection.id, JPEG)

        service.upload_library_collection_posters(MEDIA_SERVER_ID, library_id)
        connector.upload_poster.reset_mock()
        assert service.upload_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        connector.upload_poster.assert_not_called()

    def test_a_collection_with_nothing_stored_is_not_uploaded(self, db, service, connector):
        session, _ = db
        library_id = _library(session)
        _collection(session, library_id, processed=True)

        assert service.upload_library_collection_posters(MEDIA_SERVER_ID, library_id) == 0
        connector.upload_poster.assert_not_called()

    def test_an_ungenerated_collection_is_not_uploaded(self, db, store, service, connector):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        assert service.upload_library_collection_posters(MEDIA_SERVER_ID, library_id) == 0
        connector.upload_poster.assert_not_called()

    def test_a_library_that_does_not_track_collections_uploads_nothing(self, db, store, service,
                                                                       connector):
        session, _ = db
        library_id = _library(session, track_collections=False)
        collection = _collection(session, library_id, processed=True)
        store.save(library_id, collection.id, JPEG)

        assert service.upload_library_collection_posters(MEDIA_SERVER_ID, library_id) == 0
        connector.upload_poster.assert_not_called()

    def test_a_run_level_override_beats_the_library_setting(self, db, store, service, connector):
        session, _ = db
        library_id = _library(session, upload_enabled=True)
        collection = _collection(session, library_id)
        store.save(library_id, collection.id, b"server-art")

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id,
                                                           upload=False) == 1
        connector.upload_poster.assert_not_called()

class TestCatalogueWithoutServerArtwork:

    @pytest.fixture
    def aggregator(self):
        return MagicMock(get_all_collection_posters=MagicMock(return_value=[]),
                         find_collection_id=MagicMock(return_value=None))

    @pytest.fixture
    def service(self, db, store, decorator, aggregator):
        _, factory = db
        return CollectionPosterService(session_factory=factory, file_store=store,
                                       decorator=decorator,
                                       aggregator_factory=lambda _session: aggregator)

    @staticmethod
    def _member(session, library_id, collection_id):
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library_id, external_id="m1", title="Dr. No", type="movie", tmdb_id="646")])
        session.commit()
        item = service.find_items(LibraryItemSearch(library_id=library_id))[0]
        LibraryCollectionRepository(session).set_members(collection_id, [item.id])
        session.commit()

    def test_a_collection_with_no_server_artwork_still_gets_a_catalogue_poster(
            self, db, store, service, aggregator, decorator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, title="Bond", poster_url=None,
                                 tmdb_collection_id=645)
        aggregator.get_all_collection_posters.return_value = [
            ProviderPoster("http://tmdb/bond.jpg", "tmdb")]

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 1
        assert decorator.decorate_poster.call_args.args[0] == "http://tmdb/bond.jpg"
        assert store.fetch(library_id, collection.id) == JPEG

    def test_such_a_collection_is_still_reachable_by_the_resolver(self, db, service, aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, title="Bond", poster_url=None)
        self._member(session, library_id, collection.id)
        aggregator.find_collection_id.return_value = 645

        assert service.resolve_collection_ids(MEDIA_SERVER_ID, library_id) == 1

        stored = LibraryCollectionRepository(session).get_collection(library_id, collection.id)
        assert stored.tmdb_collection_id == 645

    def test_no_artwork_anywhere_is_still_a_skip_not_a_failure(self, db, service, aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, title="Handmade", poster_url=None)
        self._member(session, library_id, collection.id)

        assert service.generate_library_collection_posters(MEDIA_SERVER_ID, library_id) == 0
        stored = LibraryCollectionRepository(session).get_collection(library_id, collection.id)
        assert stored.processed is False
        assert stored.error_message is None

class TestResolution:

    @pytest.fixture
    def aggregator(self):
        return MagicMock(get_all_collection_posters=MagicMock(return_value=[]),
                         find_collection_id=MagicMock(return_value=None))

    @pytest.fixture
    def service(self, db, store, decorator, aggregator):
        _, factory = db
        return CollectionPosterService(session_factory=factory, file_store=store,
                                       decorator=decorator,
                                       aggregator_factory=lambda _session: aggregator)

    @staticmethod
    def _member(session, library_id, collection_id, tmdb_id="8091", external_id="m1"):
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library_id, external_id=external_id, title="Alien", type="movie",
            tmdb_id=tmdb_id)])
        session.commit()
        item = next(i for i in service.find_items(LibraryItemSearch(library_id=library_id))
                    if i.external_id == external_id)
        LibraryCollectionRepository(session).add_members(collection_id, [item.id])
        session.commit()

    def test_a_matched_collection_stores_its_id(self, db, service, aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        self._member(session, library_id, collection.id)
        aggregator.find_collection_id.return_value = 1234

        assert service.resolve_collection_ids(MEDIA_SERVER_ID, library_id) == 1
        stored = LibraryCollectionRepository(session).get_collection(library_id, collection.id)
        assert stored.tmdb_collection_id == 1234

    def test_the_members_are_what_it_asks_about_never_the_title(self, db, service, aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        self._member(session, library_id, collection.id, tmdb_id="8091")
        aggregator.find_collection_id.return_value = 1234

        service.resolve_collection_ids(MEDIA_SERVER_ID, library_id)

        assert aggregator.find_collection_id.call_args.args[0] == [8091]

    def test_a_collection_that_already_matched_is_never_asked_again(self, db, service, aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, tmdb_collection_id=99)
        self._member(session, library_id, collection.id)

        assert service.resolve_collection_ids(MEDIA_SERVER_ID, library_id) == 0
        aggregator.find_collection_id.assert_not_called()

    def test_a_locked_collection_is_included(self, db, service, aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id, locked=True)
        self._member(session, library_id, collection.id)
        aggregator.find_collection_id.return_value = 1234

        assert service.resolve_collection_ids(MEDIA_SERVER_ID, library_id) == 1
        stored = LibraryCollectionRepository(session).get_collection(library_id, collection.id)
        assert stored.tmdb_collection_id == 1234
        assert stored.locked is True

    def test_a_collection_with_no_catalogued_members_asks_nothing(self, db, service, aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        self._member(session, library_id, collection.id, tmdb_id=None)

        assert service.resolve_collection_ids(MEDIA_SERVER_ID, library_id) == 0
        aggregator.find_collection_id.assert_not_called()

    def test_no_match_is_not_recorded_so_a_later_sync_can_still_find_one(self, db, service,
                                                                        aggregator):
        session, _ = db
        library_id = _library(session)
        collection = _collection(session, library_id)
        self._member(session, library_id, collection.id)
        aggregator.find_collection_id.return_value = None

        assert service.resolve_collection_ids(MEDIA_SERVER_ID, library_id) == 0
        stored = LibraryCollectionRepository(session).get_collection(library_id, collection.id)
        assert stored.tmdb_collection_id is None
        assert stored.error_message is None

    def test_one_catalogue_failure_does_not_end_the_run(self, db, service, aggregator, monkeypatch):
        monkeypatch.setattr(module, "MAX_WORKERS", 1)
        session, _ = db
        library_id = _library(session)
        first = _collection(session, library_id, title="A")
        second = _collection(session, library_id, title="B")
        self._member(session, library_id, first.id, external_id="m1", tmdb_id="111")
        self._member(session, library_id, second.id, external_id="m2", tmdb_id="222")

        def catalogue(tmdb_ids):
            if 111 in tmdb_ids:
                raise RuntimeError("TMDB is down")
            return 1234

        aggregator.find_collection_id.side_effect = catalogue

        assert service.resolve_collection_ids(MEDIA_SERVER_ID, library_id) == 1

    def test_without_a_provider_it_does_nothing_rather_than_failing(self, db, store, decorator):
        session, factory = db
        library_id = _library(session)
        _collection(session, library_id)
        plain = CollectionPosterService(session_factory=factory, file_store=store,
                                        decorator=decorator)

        assert plain.resolve_collection_ids(MEDIA_SERVER_ID, library_id) == 0
