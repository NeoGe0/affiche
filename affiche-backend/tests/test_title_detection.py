from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import (
    ItemStatusFilter, Library, LibraryItem, LibraryItemSearch, LibrarySearch,
)
from affiche.app.mediaserver.library.service.item_rename_service import ItemRenameError
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.service.title_check_service import TitleCheckService
from affiche.app.mediaserver.library.title_check import matches_any, titles_differ
from affiche.app.mediaserver.library.service.title_cleanup_service import (
    FAILED,
    PENDING,
    RENAMED,
    TitleCleanupService,
)
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config import Base
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
    service.create(Library(media_server_id=server.id, external_id="sec-1", name="Films FR",
                           type="movie", language="fr-FR", enabled=True))
    db.commit()
    stored = service.find_libraries(LibrarySearch(media_server_id=server.id))[0]

    service.create_or_update_items_batch([
        LibraryItem(library_id=stored.id, external_id="100", title="My.movie.2012.1080p",
                    type="movie", tmdb_id=603),
    ])
    db.commit()
    return server.id, stored

def _item(db, library_id: int) -> LibraryItem:
    return LibraryService(db).find_items(LibraryItemSearch(library_id=library_id))[0]

def _upsert(db, library_id: int, title: str, external_id: str = "100") -> None:
    LibraryService(db).create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id=external_id, title=title, type="movie",
                    tmdb_id=603),
    ])
    db.commit()

def _checker(db, catalogue_title, alternatives=(), raises=None) -> tuple[TitleCheckService,
                                                                          MagicMock]:
    rename_service = MagicMock()
    rename_service.catalogue_title.return_value = (
        TitleMatch(title=catalogue_title, provider="tmdb") if catalogue_title else None)
    rename_service.agrees_with_catalogue.side_effect = (
        lambda _server, _library, item, primary: not titles_differ(item.title, primary)
        or matches_any(item.title, alternatives))
    if raises is not None:
        rename_service.catalogue_title.side_effect = raises
    return TitleCheckService(session_factory=lambda: db,
                             rename_service_factory=lambda _s: rename_service), rename_service

def test_a_title_the_catalogue_disagrees_with_is_flagged(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My Movie")

    report = service.check_library(server_id, lib.id)

    assert (report.checked, report.mismatched, report.skipped) == (1, 1, 0)
    assert _item(db, lib.id).title_mismatched is True

def test_a_title_the_catalogue_agrees_with_is_recorded_as_checked_not_flagged(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My.movie.2012.1080p")

    report = service.check_library(server_id, lib.id)

    item = _item(db, lib.id)
    assert (report.checked, report.mismatched) == (1, 0)
    assert item.title_mismatched is False
    assert item.title_checked_at is not None

def test_a_spelling_difference_is_not_a_disagreement(db, library):
    server_id, lib = library
    _upsert(db, lib.id, "Astérix & Obélix : Au service de Sa Majesté")
    service, _ = _checker(db, "Astérix et Obélix: Au service de sa Majesté")

    report = service.check_library(server_id, lib.id)

    assert (report.checked, report.mismatched) == (1, 0)

def test_a_title_the_catalogue_knows_under_another_name_is_not_flagged(db, library):
    server_id, lib = library
    _upsert(db, lib.id, "Act of Vengeance")
    service, _ = _checker(db, "Five Minarets in New York",
                          alternatives=["Five Minarets in New York", "Act of Vengeance",
                                        "5 Minarets à New York"])

    report = service.check_library(server_id, lib.id)

    assert (report.checked, report.mismatched) == (1, 0)
    assert _item(db, lib.id).title_mismatched is False

def test_a_release_name_matches_no_alternative_and_is_still_flagged(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My Movie",
                          alternatives=["My Movie", "Mon film", "The Movie"])

    report = service.check_library(server_id, lib.id)

    assert (report.checked, report.mismatched) == (1, 1)

def test_alternatives_are_not_fetched_when_the_primary_already_agrees(db, library):
    server_id, lib = library
    _upsert(db, lib.id, "My Movie")
    service, rename_service = _checker(db, "My Movie")

    service.check_library(server_id, lib.id)

    rename_service.catalogue_alternatives.assert_not_called()

def test_an_item_the_catalogue_cannot_answer_for_is_left_unchecked(db, library):
    server_id, lib = library
    service, _ = _checker(db, None)

    report = service.check_library(server_id, lib.id)

    item = _item(db, lib.id)
    assert (report.checked, report.skipped) == (0, 1)
    assert item.title_checked_at is None
    assert item.title_mismatched is False

def test_one_failing_item_does_not_end_the_run(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My Movie", raises=RuntimeError("tmdb exploded"))

    report = service.check_library(server_id, lib.id)

    assert (report.checked, report.skipped) == (0, 1)

def test_the_check_stops_when_cancelled(db, library):
    server_id, lib = library
    service, rename_service = _checker(db, "My Movie")

    service.check_library(server_id, lib.id, cancel_check=lambda: True)

    rename_service.catalogue_title.assert_not_called()

def test_an_item_already_checked_is_not_checked_again(db, library):
    server_id, lib = library
    service, rename_service = _checker(db, "My Movie")
    service.check_library(server_id, lib.id)
    assert rename_service.catalogue_title.call_count == 1

    service.check_library(server_id, lib.id)

    assert rename_service.catalogue_title.call_count == 1

def test_a_sync_that_changes_the_title_sends_it_back_for_a_re_check(db, library):
    server_id, lib = library
    service, rename_service = _checker(db, "My Movie")
    service.check_library(server_id, lib.id)

    _upsert(db, lib.id, "Something Else Entirely")

    assert _item(db, lib.id).title_checked_at is None
    service.check_library(server_id, lib.id)
    assert rename_service.catalogue_title.call_count == 2

def test_a_sync_that_leaves_the_title_alone_keeps_the_verdict(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My Movie")
    service.check_library(server_id, lib.id)
    assert _item(db, lib.id).title_mismatched is True

    _upsert(db, lib.id, "My.movie.2012.1080p")

    item = _item(db, lib.id)
    assert item.title_mismatched is True
    assert item.title_checked_at is not None

def test_renaming_an_item_sends_it_back_for_a_re_check(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My Movie")
    service.check_library(server_id, lib.id)

    _upsert(db, lib.id, "My Movie")

    assert _item(db, lib.id).title_checked_at is None

def test_a_forced_check_looks_at_items_that_already_carry_a_verdict(db, library):
    server_id, lib = library
    service, rename_service = _checker(db, "My Movie")
    service.check_library(server_id, lib.id)
    assert rename_service.catalogue_title.call_count == 1

    service.check_library(server_id, lib.id, force=True)

    assert rename_service.catalogue_title.call_count == 2

def test_progress_reads_as_idle_before_anything_has_run(db, library):
    _, lib = library
    service, _ = _checker(db, "My Movie")

    assert service.progress(lib.id) == type(service.progress(lib.id))()

def test_progress_is_published_per_item_so_rows_appear_as_they_are_found(db, library):
    server_id, lib = library
    service, rename_service = _checker(db, "My Movie")
    seen = []
    rename_service.catalogue_title.side_effect = lambda *a, **k: (
        seen.append(service.progress(lib.id)) or TitleMatch(title="My Movie", provider="tmdb"))

    service.check_library(server_id, lib.id)

    assert seen[0].running is True
    assert seen[0].total == 1

def test_progress_reports_the_run_as_over_once_it_is(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My Movie")

    service.check_library(server_id, lib.id)

    progress = service.progress(lib.id)
    assert progress.running is False
    assert (progress.checked, progress.total, progress.mismatched) == (1, 1, 1)

def test_a_run_that_blows_up_still_stops_reporting_itself_as_running(db, library):
    server_id, lib = library
    service, rename_service = _checker(db, "My Movie")
    rename_service.catalogue_title.side_effect = RuntimeError("tmdb exploded")

    service.check_library(server_id, lib.id)

    assert service.progress(lib.id).running is False

def test_a_library_with_nothing_to_check_is_not_left_looking_busy(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My Movie")
    service.check_library(server_id, lib.id)

    service.check_library(server_id, lib.id)

    assert service.progress(lib.id).running is False

def test_the_status_filter_lists_the_same_items_as_its_count(db, library):
    server_id, lib = library
    service, _ = _checker(db, "My Movie")
    service.check_library(server_id, lib.id)

    library_service = LibraryService(db)
    search = LibraryItemSearch(library_id=lib.id, status=ItemStatusFilter.MISMATCHED_TITLES)

    assert library_service.count_items(search) == 1
    assert library_service.count_status_buckets(
        LibraryItemSearch(library_id=lib.id)).mismatched_titles == 1
    assert [i.title for i in library_service.find_items(search)] == ["My.movie.2012.1080p"]

def test_an_unchecked_library_flags_nothing(db, library):
    _, lib = library

    assert LibraryService(db).count_status_buckets(
        LibraryItemSearch(library_id=lib.id)).mismatched_titles == 0

def test_status_and_the_raw_predicate_cannot_be_passed_together(db):
    with pytest.raises(ValueError):
        LibraryItemSearch(library_id=1, status=ItemStatusFilter.MISMATCHED_TITLES,
                          title_mismatched=False)

def _cleanup(db, rename=True) -> tuple[TitleCleanupService, MagicMock]:
    rename_service = MagicMock()
    if isinstance(rename, Exception):
        rename_service.rename_item.side_effect = rename
    return TitleCleanupService(session_factory=lambda: db,
                               rename_service_factory=lambda _s: rename_service), rename_service

@pytest.fixture
def flagged(db, library):
    server_id, lib = library
    item = _item(db, lib.id)
    item.title_mismatched = True
    item.catalogue_title = "My Movie"
    item.title_checked_at = datetime(2026, 9, 21, 12, 0, 0)
    LibraryService(db).library_repo.create_or_update_item(item)
    db.commit()
    return server_id, lib, item.id

def test_the_panel_lists_what_would_change_without_asking_the_catalogue(db, flagged):
    server_id, lib, item_id = flagged
    service, rename_service = _cleanup(db)

    proposals = service.proposals(server_id, lib.id)

    assert [(p.item_id, p.current_title, p.proposed_title, p.status) for p in proposals] == [
        (item_id, "My.movie.2012.1080p", "My Movie", PENDING)]
    rename_service.rename_item.assert_not_called()

def test_an_item_checked_and_found_to_agree_is_not_proposed(db, library):
    server_id, lib = library
    service, _ = _cleanup(db)

    assert service.proposals(server_id, lib.id) == []

def test_a_flagged_item_with_no_stored_catalogue_title_is_not_proposed(db, library):
    server_id, lib = library
    item = _item(db, lib.id)
    item.title_mismatched = True
    LibraryService(db).library_repo.create_or_update_item(item)
    db.commit()
    service, _ = _cleanup(db)

    assert service.proposals(server_id, lib.id) == []

def test_only_the_approved_rows_are_renamed(db, flagged):
    server_id, lib, item_id = flagged
    service, rename_service = _cleanup(db)

    report = service.apply(server_id, lib.id, [item_id])

    assert (report.approved, report.renamed, report.failed) == (1, 1, 0)
    rename_service.rename_item.assert_called_once_with(server_id, lib.id, item_id, "My Movie")

def test_a_row_left_unticked_is_not_touched(db, flagged):
    server_id, lib, _ = flagged
    service, rename_service = _cleanup(db)

    report = service.apply(server_id, lib.id, [99999])

    assert report.approved == 0
    rename_service.rename_item.assert_not_called()

def test_an_id_that_was_never_proposed_cannot_be_renamed_through_the_request(db, library):
    server_id, lib = library
    unflagged = _item(db, lib.id)
    service, rename_service = _cleanup(db)

    report = service.apply(server_id, lib.id, [unflagged.id])

    assert report.approved == 0
    rename_service.rename_item.assert_not_called()

def test_a_finished_row_stays_visible_when_the_panel_is_reopened(db, flagged):
    server_id, lib, item_id = flagged
    service, _ = _cleanup(db)
    service.apply(server_id, lib.id, [item_id])

    proposals = service.proposals(server_id, lib.id)

    assert [(p.item_id, p.status) for p in proposals] == [(item_id, RENAMED)]

def test_a_refused_rename_is_reported_against_its_own_row(db, flagged):
    server_id, lib, item_id = flagged
    service, _ = _cleanup(db, rename=ItemRenameError("Plex would not."))

    report = service.apply(server_id, lib.id, [item_id])

    assert (report.renamed, report.failed) == (0, 1)
    row = service.proposals(server_id, lib.id)[0]
    assert (row.status, row.error) == (FAILED, "Plex would not.")

def test_one_failing_row_does_not_end_the_run(db, flagged):
    server_id, lib, item_id = flagged
    service, _ = _cleanup(db, rename=RuntimeError("boom"))

    report = service.apply(server_id, lib.id, [item_id])

    assert (report.approved, report.failed) == (1, 1)
    assert service.proposals(server_id, lib.id)[0].status == FAILED

def test_only_what_was_renamed_is_offered_for_regeneration(db, flagged):
    server_id, lib, item_id = flagged
    service, _ = _cleanup(db, rename=ItemRenameError("no"))
    service.apply(server_id, lib.id, [item_id])

    assert service.renamed_item_ids(lib.id) == []

def test_renamed_ids_are_what_the_regeneration_chains_onto(db, flagged):
    server_id, lib, item_id = flagged
    service, _ = _cleanup(db)
    service.apply(server_id, lib.id, [item_id])

    assert service.renamed_item_ids(lib.id) == [item_id]

def test_the_run_stops_when_cancelled(db, flagged):
    server_id, lib, item_id = flagged
    service, rename_service = _cleanup(db)

    report = service.apply(server_id, lib.id, [item_id], cancel_check=lambda: True)

    assert report.renamed == 0
    rename_service.rename_item.assert_not_called()

def test_renaming_invalidates_the_verdict_about_the_title_it_replaced(db, flagged):
    server_id, lib, item_id = flagged
    from affiche.app.mediaserver.library.service.item_rename_service import ItemRenameService

    connector = MagicMock()
    connector.rename_item.return_value = True
    factory = MagicMock()
    factory.get.return_value = connector
    ItemRenameService(db, connector_factory=factory).rename_item(
        server_id, lib.id, item_id, "My Movie")

    item = _item(db, lib.id)
    assert item.title_mismatched is False
    assert item.title_checked_at is None
