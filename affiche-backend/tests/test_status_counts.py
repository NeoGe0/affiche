import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import (
    NO_PROVIDER, ItemStatusFilter, Library, LibraryItem, LibraryItemSearch,
    LibrarySearch,
)
from affiche.app.mediaserver.library.seasons.connector.library_season_entity import (
    LibrarySeasonEntity,
)
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config import Base

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

def _seed(db, library_id: int, items: list[dict]) -> None:
    service = LibraryService(db)
    service.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id=f"e{i}", type="movie", **item)
        for i, item in enumerate(items)
    ])
    repo = LibraryRepository(db)
    stored = {item.title: item
              for item in service.find_items(LibraryItemSearch(library_id=library_id))}
    for item in items:
        entity = stored[item["title"]]
        entity.processed = item.get("processed", False)
        entity.error_message = item.get("error_message")
        entity.poster_provider = item.get("poster_provider")
        repo.create_or_update_item(entity)
    db.commit()

def _listing_count(db, library_id: int, status, search=None) -> int:
    return LibraryService(db).count_items(
        LibraryItemSearch(library_id=library_id, search=search, status=status))

def _assert_agrees_with_listing(db, library_id: int, search=None):
    stats = LibraryService(db).count_status_buckets(
        LibraryItemSearch(library_id=library_id, search=search))
    assert stats.total == _listing_count(db, library_id, None, search)
    assert stats.unprocessed == _listing_count(db, library_id, ItemStatusFilter.UNPROCESSED, search)
    assert stats.errors == _listing_count(db, library_id, ItemStatusFilter.ERRORS, search)
    assert stats.locked == _listing_count(db, library_id, ItemStatusFilter.LOCKED, search)
    return stats.total, stats.unprocessed, stats.errors

def test_buckets_split_pending_processed_and_failed(db, library_id):
    _seed(db, library_id, [
        {"title": "Pending One"},
        {"title": "Pending Two"},
        {"title": "Done", "processed": True},
        {"title": "Failed", "error_message": "No poster found"},
    ])

    assert _assert_agrees_with_listing(db, library_id) == (4, 2, 1)

def test_a_failed_item_is_not_also_counted_as_unprocessed(db, library_id):
    _seed(db, library_id, [{"title": "Failed", "error_message": "boom"}])

    assert _assert_agrees_with_listing(db, library_id) == (1, 0, 1)

def test_a_processed_item_that_later_failed_still_counts_as_an_error(db, library_id):
    _seed(db, library_id, [{"title": "Was Fine", "processed": True, "error_message": "upload failed"}])

    assert _assert_agrees_with_listing(db, library_id) == (1, 0, 1)

def test_counts_follow_the_search(db, library_id):
    _seed(db, library_id, [
        {"title": "Alien"},
        {"title": "Aliens", "error_message": "boom"},
        {"title": "Blade Runner", "processed": True},
    ])

    assert _assert_agrees_with_listing(db, library_id, search="alien") == (2, 1, 1)

def test_an_empty_library_reports_zeroes_not_nulls(db, library_id):
    stats = LibraryService(db).count_status_buckets(LibraryItemSearch(library_id=library_id))
    assert (stats.total, stats.unprocessed, stats.errors, stats.locked) == (0, 0, 0, 0)

def test_attempted_covers_processed_and_failed_but_not_pending(db, library_id):
    _seed(db, library_id, [
        {"title": "Done", "processed": True},
        {"title": "Failed", "error_message": "boom"},
        {"title": "Failed After Success", "processed": True, "error_message": "upload failed"},
        {"title": "Pending"},
    ])
    service = LibraryService(db)

    attempted = service.find_items(LibraryItemSearch(library_id=library_id, attempted=True))
    untouched = service.find_items(LibraryItemSearch(library_id=library_id, attempted=False))

    assert sorted(i.title for i in attempted) == ["Done", "Failed", "Failed After Success"]
    assert [i.title for i in untouched] == ["Pending"]

def test_deleted_items_are_excluded(db, library_id):
    from datetime import datetime, timezone

    _seed(db, library_id, [{"title": "Gone"}, {"title": "Here"}])
    service = LibraryService(db)
    gone = next(i for i in service.find_items(LibraryItemSearch(library_id=library_id)) if i.title == "Gone")
    gone.deleted_at = datetime.now(timezone.utc)
    LibraryRepository(db).create_or_update_item(gone)
    db.commit()

    assert _assert_agrees_with_listing(db, library_id) == (1, 1, 0)

def _provider_listing_count(db, library_id: int, provider, status=None) -> int:
    return LibraryService(db).count_items(
        LibraryItemSearch(library_id=library_id, provider=provider, status=status))

def test_provider_buckets_agree_with_the_listing(db, library_id):
    _seed(db, library_id, [
        {"title": "A", "processed": True, "poster_provider": "tmdb"},
        {"title": "B", "processed": True, "poster_provider": "tmdb"},
        {"title": "C", "processed": True, "poster_provider": "mediux"},
        {"title": "D"},
    ])

    counts = LibraryService(db).count_items_by_provider(LibraryItemSearch(library_id=library_id))

    assert counts == {"tmdb": 2, "mediux": 1, None: 1}
    for provider, count in counts.items():
        assert count == _provider_listing_count(db, library_id, provider or NO_PROVIDER)

def test_a_provider_this_library_holds_nothing_from_is_absent(db, library_id):
    _seed(db, library_id, [{"title": "A", "processed": True, "poster_provider": "tmdb"}])

    assert "shoko" not in LibraryService(db).count_items_by_provider(LibraryItemSearch(library_id=library_id))

def test_status_buckets_narrow_to_the_chosen_provider(db, library_id):
    _seed(db, library_id, [
        {"title": "A", "processed": True, "poster_provider": "tmdb"},
        {"title": "B", "error_message": "boom", "poster_provider": "tmdb"},
        {"title": "C", "error_message": "boom", "poster_provider": "mediux"},
    ])

    stats = LibraryService(db).count_status_buckets(
        LibraryItemSearch(library_id=library_id, provider="tmdb"))

    assert (stats.total, stats.errors) == (2, 1)
    assert stats.errors == _provider_listing_count(
        db, library_id, "tmdb", ItemStatusFilter.ERRORS)

def test_provider_buckets_narrow_to_the_chosen_status(db, library_id):
    _seed(db, library_id, [
        {"title": "A", "processed": True, "poster_provider": "tmdb"},
        {"title": "B", "error_message": "boom", "poster_provider": "tmdb"},
        {"title": "C", "error_message": "boom", "poster_provider": "mediux"},
    ])

    counts = LibraryService(db).count_items_by_provider(
        LibraryItemSearch(library_id=library_id, status=ItemStatusFilter.ERRORS))

    assert counts == {"tmdb": 1, "mediux": 1}

def _seed_season(db, library_id: int, show_title: str, provider, season_number: int = 1) -> None:
    show = {item.title: item for item in
            LibraryService(db).find_items(LibraryItemSearch(library_id=library_id))}[show_title]
    db.add(LibrarySeasonEntity(show_id=show.id, library_id=library_id,
                               external_id=f"s-{show.id}-{season_number}",
                               season_number=season_number, title=f"Season {season_number}",
                               poster_provider=provider, processed=provider is not None))
    db.commit()

def test_an_item_matches_a_provider_that_only_supplied_its_season_art(db, library_id):
    _seed(db, library_id, [{"title": "Show", "processed": True, "poster_provider": "tmdb"},
                           {"title": "Other", "processed": True, "poster_provider": "tmdb"}])
    _seed_season(db, library_id, "Show", "mediux")

    found = LibraryService(db).find_items(
        LibraryItemSearch(library_id=library_id, provider="mediux"))

    assert [item.title for item in found] == ["Show"]

def test_such_a_provider_is_offered_as_a_bucket(db, library_id):
    _seed(db, library_id, [{"title": "Show", "processed": True, "poster_provider": "tmdb"}])
    _seed_season(db, library_id, "Show", "mediux")

    counts = LibraryService(db).count_items_by_provider(LibraryItemSearch(library_id=library_id))

    assert counts == {"tmdb": 1, "mediux": 1}
    for provider, count in counts.items():
        assert count == _provider_listing_count(db, library_id, provider)

def test_an_item_is_only_unrecorded_when_nothing_about_it_is_recorded(db, library_id):
    _seed(db, library_id, [{"title": "Show"}, {"title": "Bare"}])
    _seed_season(db, library_id, "Show", "mediux")

    found = LibraryService(db).find_items(
        LibraryItemSearch(library_id=library_id, provider=NO_PROVIDER))

    assert [item.title for item in found] == ["Bare"]

def test_an_item_is_counted_once_however_many_of_its_seasons_match(db, library_id):
    _seed(db, library_id, [{"title": "Show", "processed": True, "poster_provider": "tmdb"}])
    _seed_season(db, library_id, "Show", "mediux", season_number=1)
    _seed_season(db, library_id, "Show", "mediux", season_number=2)

    counts = LibraryService(db).count_items_by_provider(LibraryItemSearch(library_id=library_id))

    assert counts["mediux"] == 1

def test_the_poster_breakdown_counts_seasons_as_posters_of_their_own(db, library_id):
    _seed(db, library_id, [{"title": "Show", "processed": True, "poster_provider": "tmdb"}])
    _seed_season(db, library_id, "Show", "mediux", season_number=1)
    _seed_season(db, library_id, "Show", "mediux", season_number=2)

    counts = LibraryService(db).count_posters_by_provider(LibraryItemSearch(library_id=library_id))

    assert counts == {"tmdb": 1, "mediux": 2}
