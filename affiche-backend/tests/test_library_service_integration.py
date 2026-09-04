import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibrarySearch
from affiche.app.mediaserver.library.model import LibraryItemSearch, SortDir

@pytest.fixture
def media_server(session: Session):
    connector = MediaServerPersistenceConnector(session)

    server = MediaServer(
        name="Test Server",
        type=MediaServerType.PLEX,
        url="http://localhost:32400",
        token="test-token"
    )

    entity = connector.create(server)
    session.flush()

    return MediaServer.model_validate(entity)

class TestLibraryServiceCreate:

    def test_create_library(self, session: Session, media_server):
        library_service = LibraryService(session)

        library = Library(
            media_server_id=media_server.id,
            external_id="lib-1",
            name="Movies",
            type="movie",
            language="en",
            enabled=True
        )

        library_service.create(library)
        session.flush()

        found = library_service.find_libraries(LibrarySearch(media_server_id=media_server.id))
        assert len(found) == 1
        assert found[0].name == "Movies"
        assert found[0].external_id == "lib-1"

    def test_create_multiple_libraries(self, session: Session, media_server):
        library_service = LibraryService(session)

        libraries = [
            Library(
                media_server_id=media_server.id,
                external_id=f"lib-{i}",
                name=f"Library {i}",
                type="movie" if i % 2 == 0 else "show",
                language="en",
                enabled=True
            )
            for i in range(3)
        ]

        for lib in libraries:
            library_service.create(lib)
        session.flush()

        found = library_service.find_libraries(LibrarySearch(media_server_id=media_server.id))
        assert len(found) == 3

class TestLibraryServiceFind:

    def test_find_libraries_by_media_server(self, session: Session, media_server):
        library_service = LibraryService(session)

        for name in ["Movies", "TV Shows", "Anime"]:
            library = Library(
                media_server_id=media_server.id,
                external_id=f"lib-{name.lower().replace(' ', '-')}",
                name=name,
                type="movie",
                language="en",
                enabled=True
            )
            library_service.create(library)
        session.flush()

        libraries = library_service.find_libraries(LibrarySearch(media_server_id=media_server.id))

        assert len(libraries) == 3
        library_names = {lib.name for lib in libraries}
        assert "Movies" in library_names
        assert "TV Shows" in library_names
        assert "Anime" in library_names

    def test_find_libraries_enabled_only(self, session: Session, media_server):
        library_service = LibraryService(session)

        lib1 = Library(
            media_server_id=media_server.id,
            external_id="enabled-lib",
            name="Enabled Library",
            type="movie",
            language="en",
            enabled=True
        )
        lib2 = Library(
            media_server_id=media_server.id,
            external_id="disabled-lib",
            name="Disabled Library",
            type="movie",
            language="en",
            enabled=False
        )

        library_service.create(lib1)
        library_service.create(lib2)
        session.flush()

        enabled = library_service.find_libraries(LibrarySearch(media_server_id=media_server.id, enabled=True))

        assert len(enabled) == 1
        assert enabled[0].name == "Enabled Library"

    def test_get_library(self, session: Session, media_server):
        library_service = LibraryService(session)

        library = Library(
            media_server_id=media_server.id,
            external_id="get-lib",
            name="Get Test Library",
            type="show",
            language="en",
            enabled=True
        )
        library_service.create(library)
        session.flush()

        libraries = library_service.find_libraries(LibrarySearch(media_server_id=media_server.id))
        library_id = libraries[0].id

        found = library_service.get_library(media_server.id, library_id)

        assert found is not None
        assert found.name == "Get Test Library"

class TestLibraryServiceItems:

    @pytest.fixture
    def movie_library(self, session: Session, media_server):
        library_service = LibraryService(session)

        library = Library(
            media_server_id=media_server.id,
            external_id="movies-lib",
            name="Movies",
            type="movie",
            language="en",
            enabled=True
        )
        library_service.create(library)
        session.flush()

        libraries = library_service.find_libraries(LibrarySearch(media_server_id=media_server.id))
        return libraries[0]

    def test_create_or_update_items_batch(self, session: Session, movie_library):
        library_service = LibraryService(session)

        items = [
            LibraryItem(
                library_id=movie_library.id,
                external_id="movie-1",
                title="The Matrix",
                type="movie",
                year=1999,
                imdb_id="tt0133093",
                tmdb_id=603,
                added_at=datetime.now(timezone.utc)
            ),
            LibraryItem(
                library_id=movie_library.id,
                external_id="movie-2",
                title="Inception",
                type="movie",
                year=2010,
                imdb_id="tt1375666",
                tmdb_id=27205,
                added_at=datetime.now(timezone.utc)
            ),
            LibraryItem(
                library_id=movie_library.id,
                external_id="movie-3",
                title="Interstellar",
                type="movie",
                year=2014,
                imdb_id="tt0816692",
                tmdb_id=157336,
                added_at=datetime.now(timezone.utc)
            )
        ]

        library_service.create_or_update_items_batch(items)
        session.flush()

        found_items = library_service.find_items(LibraryItemSearch(library_id=movie_library.id))
        assert len(found_items) == 3

        titles = {item.title for item in found_items}
        assert "The Matrix" in titles
        assert "Inception" in titles
        assert "Interstellar" in titles

    def test_get_items_by_library_with_search(self, session: Session, movie_library):
        library_service = LibraryService(session)

        items = [
            LibraryItem(
                library_id=movie_library.id,
                external_id="movie-1",
                title="The Matrix",
                type="movie",
                year=1999
            ),
            LibraryItem(
                library_id=movie_library.id,
                external_id="movie-2",
                title="The Matrix Reloaded",
                type="movie",
                year=2003
            ),
            LibraryItem(
                library_id=movie_library.id,
                external_id="movie-3",
                title="Inception",
                type="movie",
                year=2010
            )
        ]
        library_service.create_or_update_items_batch(items)
        session.flush()

        found = library_service.find_items(LibraryItemSearch(library_id=movie_library.id, search="Matrix"))

        assert len(found) == 2
        for item in found:
            assert "Matrix" in item.title

    def test_get_items_by_library_with_pagination(self, session: Session, movie_library):
        library_service = LibraryService(session)

        items = [
            LibraryItem(
                library_id=movie_library.id,
                external_id=f"movie-{i}",
                title=f"Movie {i}",
                type="movie",
                year=2000 + i
            )
            for i in range(10)
        ]
        library_service.create_or_update_items_batch(items)
        session.flush()

        page1 = library_service.find_items(LibraryItemSearch(library_id=movie_library.id, page=0, page_size=5))
        assert len(page1) == 5

        page2 = library_service.find_items(LibraryItemSearch(library_id=movie_library.id, page=1, page_size=5))
        assert len(page2) == 5

        page1_ids = {item.external_id for item in page1}
        page2_ids = {item.external_id for item in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_count_items_by_library(self, session: Session, movie_library):
        library_service = LibraryService(session)

        items = [
            LibraryItem(
                library_id=movie_library.id,
                external_id=f"movie-{i}",
                title=f"Movie {i}",
                type="movie",
                year=2000 + i
            )
            for i in range(15)
        ]
        library_service.create_or_update_items_batch(items)
        session.flush()

        count = library_service.count_items(LibraryItemSearch(library_id=movie_library.id))

        assert count == 15

    def test_get_items_by_external_ids(self, session: Session, movie_library):
        library_service = LibraryService(session)

        items = [
            LibraryItem(
                library_id=movie_library.id,
                external_id=f"ext-{i}",
                title=f"Movie {i}",
                type="movie",
                year=2000 + i
            )
            for i in range(5)
        ]
        library_service.create_or_update_items_batch(items)
        session.flush()

        found = library_service.find_items(LibraryItemSearch(
            library_id=movie_library.id,
            external_ids=["ext-1", "ext-3", "ext-999"],
        ))

        assert len(found) == 2
        external_ids = {item.external_id for item in found}
        assert "ext-1" in external_ids
        assert "ext-3" in external_ids
        assert "ext-999" not in external_ids

    def test_update_existing_items_in_batch(self, session: Session, movie_library):
        library_service = LibraryService(session)

        items = [
            LibraryItem(
                library_id=movie_library.id,
                external_id="movie-1",
                title="Old Title",
                type="movie",
                year=1999
            )
        ]
        library_service.create_or_update_items_batch(items)
        session.flush()

        updated_items = [
            LibraryItem(
                library_id=movie_library.id,
                external_id="movie-1",
                title="New Title",
                type="movie",
                year=2000
            )
        ]
        library_service.create_or_update_items_batch(updated_items)
        session.flush()

        found = library_service.find_items(LibraryItemSearch(library_id=movie_library.id))
        assert len(found) == 1
        assert found[0].title == "New Title"
        assert found[0].year == 2000
        assert found[0].processed is False

    def test_filter_by_processed_status(self, session: Session, movie_library):
        from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity

        library_service = LibraryService(session)

        items = [
            LibraryItem(
                library_id=movie_library.id,
                external_id=f"movie-{i}",
                title=f"Movie {i}",
                type="movie",
                year=2000
            )
            for i in range(6)
        ]
        library_service.create_or_update_items_batch(items)
        session.flush()

        all_items = session.query(LibraryItemEntity).filter(
            LibraryItemEntity.library_id == movie_library.id
        ).all()
        for i, item in enumerate(all_items):
            if i % 2 == 0:
                item.processed = True
        session.flush()

        processed = library_service.find_items(LibraryItemSearch(library_id=movie_library.id, processed=True))
        assert len(processed) == 3
        for item in processed:
            assert item.processed is True

        unprocessed = library_service.find_items(LibraryItemSearch(library_id=movie_library.id, processed=False))
        assert len(unprocessed) == 3
        for item in unprocessed:
            assert item.processed is False

    def test_batch_upsert_stamps_and_refreshes_last_seen_at(self, session: Session, movie_library):
        library_service = LibraryService(session)
        t1 = datetime(2020, 1, 1, 12, 0, 0)
        t2 = datetime(2021, 6, 15, 8, 30, 0)

        library_service.create_or_update_items_batch([
            LibraryItem(library_id=movie_library.id, external_id="m-1",
                        title="Movie", type="movie", last_seen_at=t1)
        ])
        session.flush()
        assert library_service.find_items(LibraryItemSearch(library_id=movie_library.id))[0].last_seen_at == t1

        library_service.create_or_update_items_batch([
            LibraryItem(library_id=movie_library.id, external_id="m-1",
                        title="Movie", type="movie", last_seen_at=t2)
        ])
        session.flush()
        assert library_service.find_items(LibraryItemSearch(library_id=movie_library.id))[0].last_seen_at == t2

    def test_batch_upsert_preserves_poster_uploaded_at(self, session: Session, movie_library):
        from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity

        library_service = LibraryService(session)
        library_service.create_or_update_items_batch([
            LibraryItem(library_id=movie_library.id, external_id="m-1",
                        title="Movie", type="movie", last_seen_at=datetime(2020, 1, 1))
        ])
        session.flush()

        uploaded_at = datetime(2022, 3, 3, 9, 0, 0)
        entity = session.query(LibraryItemEntity).filter_by(
            library_id=movie_library.id, external_id="m-1").one()
        entity.poster_uploaded_at = uploaded_at
        session.flush()

        library_service.create_or_update_items_batch([
            LibraryItem(library_id=movie_library.id, external_id="m-1",
                        title="Movie Renamed", type="movie", last_seen_at=datetime(2023, 1, 1))
        ])
        session.flush()

        found = library_service.find_items(LibraryItemSearch(library_id=movie_library.id))[0]
        assert found.title == "Movie Renamed"
        assert found.poster_uploaded_at == uploaded_at
