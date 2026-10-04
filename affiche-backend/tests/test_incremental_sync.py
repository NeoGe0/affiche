from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from affiche.app.asynch.auto_pickup import dispatch_library_pickup
from affiche.app.mediaserver.connector.media_server_entity import MediaServerEntity
from affiche.app.mediaserver.library.connector.library_entity import LibraryEntity
from affiche.app.mediaserver.library.settings.connector.library_settings_entity import (
    LibrarySettingsEntity,
)
from affiche.app.mediaserver.library.settings.model.library_settings import AutoPickupAction
from affiche.app.mediaserver.library.sync.incremental import (
    FULL_SYNC_MAX_AGE, RECENT_ITEM_LIMIT, may_run_incrementally, shows_gaining_seasons,
)
from affiche.app.mediaserver.model.media_server import MediaServerType
from affiche.app.mediaserver.service.jellyfin_sync_service import JellyfinSynchronisationService
from affiche.app.mediaserver.service.plex_sync_service import PlexSynchronisationService
from affiche.external.jellyfin.service.jellyfin_service import JellyfinService
from affiche.external.media_quality import MEDIA_FIELDS as _MEDIA_FIELDS
from affiche.external.plex.service.plex_service import PlexService

NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

def test_a_library_never_seen_whole_is_synced_in_full():
    assert may_run_incrementally(None, NOW) is False

def test_a_recent_full_sync_allows_an_incremental_run():
    assert may_run_incrementally(NOW - timedelta(hours=1), NOW) is True

def test_a_stale_full_sync_forces_a_full_run():
    assert may_run_incrementally(NOW - FULL_SYNC_MAX_AGE - timedelta(minutes=1), NOW) is False

def test_a_naive_watermark_is_read_as_utc():
    assert may_run_incrementally(datetime(2026, 8, 31, 11, 0), NOW) is True

def _item(i):
    return SimpleNamespace(id=i, title=f"t{i}", type="movie", year=2000, release_date=None,
                           added_at=None, updated_at=None, imdb_id=None, tmdb_id=None,
                           tvdb_id=None, poster_url=None,
                           **{f: None for f in _MEDIA_FIELDS})

def _jellyfin(recent, full=None):
    library_service = MagicMock()
    library_service.reconcile_deletions.return_value = (0, 0)
    settings_service = MagicMock()
    factory = MagicMock()
    factory.get.return_value = MagicMock(spec=JellyfinService)
    svc = JellyfinSynchronisationService(
        library_service, settings_service, MagicMock(), MagicMock(), MagicMock(), MagicMock(),
        factory)
    connector = MagicMock()
    connector.get_recently_added_items.return_value = recent
    connector.get_library_items.return_value = full if full is not None else recent
    return svc, library_service, settings_service, connector

def _plex(recent, full=None):
    library_service = MagicMock()
    library_service.reconcile_deletions.return_value = (0, 0)
    settings_service = MagicMock()
    factory = MagicMock()
    factory.get.return_value = MagicMock(spec=PlexService)
    svc = PlexSynchronisationService(
        library_service, settings_service, MagicMock(), MagicMock(), MagicMock(), MagicMock(),
        factory)
    connector = MagicMock()
    connector.get_recently_added_items.return_value = recent
    connector.get_library_items.return_value = full if full is not None else recent
    return svc, library_service, settings_service, connector

LIBRARY = SimpleNamespace(name="L", external_id="7", id=7, type="movie")
SHOW_LIBRARY = SimpleNamespace(name="S", external_id="8", id=8, type="show")

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_incremental_fetches_only_the_newest_items(build, run):
    svc, library_service, _, connector = build([_item(1)])

    getattr(svc, run)(connector, LIBRARY, incremental=True)

    connector.get_recently_added_items.assert_called_once()
    connector.get_library_items.assert_not_called()
    library_service.create_or_update_items_batch.assert_called_once()

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_incremental_never_reconciles_deletions(build, run):
    svc, library_service, _, connector = build([_item(1)])

    getattr(svc, run)(connector, LIBRARY, incremental=True)

    library_service.reconcile_deletions.assert_not_called()

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_incremental_does_not_claim_a_full_sync(build, run):
    svc, _, settings_service, connector = build([_item(1)])

    getattr(svc, run)(connector, LIBRARY, incremental=True)

    settings_service.mark_full_sync.assert_not_called()

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_a_full_pass_stamps_the_watermark(build, run):
    svc, _, settings_service, connector = build([_item(1)])

    getattr(svc, run)(connector, LIBRARY)

    settings_service.mark_full_sync.assert_called_once()
    assert settings_service.mark_full_sync.call_args.args[0] == 7

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_a_filled_window_falls_back_to_a_full_enumeration(build, run):
    recent = [_item(i) for i in range(RECENT_ITEM_LIMIT)]
    svc, library_service, settings_service, connector = build(recent, full=recent + [_item(999)])

    getattr(svc, run)(connector, LIBRARY, incremental=True)

    connector.get_library_items.assert_called_once()
    library_service.reconcile_deletions.assert_called_once()
    settings_service.mark_full_sync.assert_called_once()

def test_a_season_we_hold_asks_for_nothing():
    assert shows_gaining_seasons({"s1": "show-a"}, {"s1"}, set()) == []

def test_a_new_season_names_its_show_once():
    recent = {"s1": "show-a", "s2": "show-a", "s3": "show-b", "s4": "show-c"}

    assert shows_gaining_seasons(recent, {"s4"}, set()) == ["show-a", "show-b"]

def test_a_show_the_item_window_already_lists_is_left_to_it():
    assert shows_gaining_seasons({"s1": "show-a"}, set(), {"show-a"}) == []

def test_a_window_of_nothing_but_new_seasons_gives_up():
    recent = {f"s{i}": f"show-{i}" for i in range(RECENT_ITEM_LIMIT)}

    assert shows_gaining_seasons(recent, set(), set()) is None

def _show(i):
    show = _item(i)
    show.type = "show"
    return show

def _with_seasons(build, recent_seasons, known):
    svc, library_service, settings_service, connector = build([_item(1)], full=[_item(1), _item(2)])
    connector.get_recently_added_seasons.return_value = recent_seasons
    connector.get_library_item.side_effect = lambda show_id, *_: _show(show_id)
    connector.get_show_seasons.return_value = []
    svc.season_service = MagicMock()
    svc.season_service.find_known_external_ids.return_value = known
    svc._sync_seasons = MagicMock()
    svc._episodes_tracked = lambda library: False
    return svc, library_service, settings_service, connector

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_incremental_rereads_an_old_show_that_gained_a_season(build, run):
    svc, library_service, _, connector = _with_seasons(build, {"s9": "42"}, known=set())

    getattr(svc, run)(connector, SHOW_LIBRARY, incremental=True)

    connector.get_library_items.assert_not_called()
    assert [show.id for show in svc._sync_seasons.call_args.args[2]] == ["42"]
    library_service.reconcile_deletions.assert_not_called()

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_incremental_fetches_no_show_when_every_recent_season_is_known(build, run):
    svc, _, _, connector = _with_seasons(build, {"s9": "42"}, known={"s9"})

    getattr(svc, run)(connector, SHOW_LIBRARY, incremental=True)

    connector.get_library_item.assert_not_called()
    svc._sync_seasons.assert_not_called()

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_a_window_full_of_new_seasons_falls_back_to_a_full_enumeration(build, run):
    recent = {f"s{i}": f"show-{i}" for i in range(RECENT_ITEM_LIMIT)}
    svc, _, settings_service, connector = _with_seasons(build, recent, known=set())

    getattr(svc, run)(connector, SHOW_LIBRARY, incremental=True)

    connector.get_library_items.assert_called_once()
    settings_service.mark_full_sync.assert_called_once()

@pytest.mark.parametrize("build,run", [
    (_jellyfin, "_sync_single_library"),
    (_plex, "_sync_library"),
])
def test_a_failed_season_lookup_does_not_fail_the_pass(build, run):
    svc, library_service, _, connector = _with_seasons(build, {}, known=set())
    connector.get_recently_added_seasons.side_effect = RuntimeError("server said no")

    getattr(svc, run)(connector, SHOW_LIBRARY, incremental=True)

    connector.get_library_items.assert_not_called()
    library_service.create_or_update_items_batch.assert_called_once()

class _RecordingTaskService:
    def __init__(self):
        self.kwargs = []

    def submit_detached_task(self, task_func, task_name, blocking=False, resource=None, **kw):
        self.kwargs.append({"task_name": task_name, "task_func": task_func})
        return "task-id", "pending"

@pytest.mark.parametrize("action", list(AutoPickupAction))
def test_incremental_rides_the_same_task_name_as_a_full_run(action):
    svc = _RecordingTaskService()
    dispatch_library_pickup(svc, 2, 5, action, incremental=True)
    dispatch_library_pickup(svc, 2, 5, action, incremental=False)

    assert svc.kwargs[0]["task_name"] == svc.kwargs[1]["task_name"]

def test_dispatch_passes_the_mode_down_to_the_task(monkeypatch):
    import affiche.app.asynch.auto_pickup as auto_pickup
    seen = {}
    monkeypatch.setattr(auto_pickup, "sync_library_task",
                        lambda ms, lib, cancel_check=None, incremental=False:
                        seen.update(incremental=incremental))

    svc = _RecordingTaskService()
    dispatch_library_pickup(svc, 2, 5, AutoPickupAction.SYNC, incremental=True)
    svc.kwargs[0]["task_func"]()

    assert seen == {"incremental": True}

def _seed_due_library(session, last_full_sync_at):
    ms = MediaServerEntity(name="P", type=MediaServerType.PLEX, url="u", token="t", enabled=True)
    session.add(ms); session.flush()
    lib = LibraryEntity(media_server_id=ms.id, external_id="1", name="Films", type="movie",
                        language="en", enabled=True)
    session.add(lib); session.flush()
    session.add(LibrarySettingsEntity(library_id=lib.id, auto_sync_enabled=True,
                                      auto_sync_interval_minutes=360,
                                      auto_pickup_action="sync",
                                      last_auto_sync_at=None,
                                      last_full_sync_at=last_full_sync_at))
    session.commit()
    return lib

def _tick_mode(session, monkeypatch, last_full_sync_at):
    from sqlalchemy.orm import sessionmaker

    import affiche.app.asynch.auto_sync_scheduler as scheduler

    _seed_due_library(session, last_full_sync_at)
    monkeypatch.setattr(scheduler, "SessionLocal",
                        sessionmaker(bind=session.get_bind()))
    seen = {}
    monkeypatch.setattr(scheduler, "dispatch_library_pickup",
                        lambda *a, incremental=False, **k:
                        (seen.update(incremental=incremental), ("t", "pending"))[1])

    scheduler.AutoSyncScheduler().tick()
    return seen

def test_scheduler_runs_a_never_fully_synced_library_in_full(clean_session, monkeypatch):
    assert _tick_mode(clean_session, monkeypatch, None) == {"incremental": False}

def test_scheduler_runs_incrementally_after_a_recent_full_sync(clean_session, monkeypatch):
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    assert _tick_mode(clean_session, monkeypatch, recent) == {"incremental": True}

def test_scheduler_forces_a_full_run_once_the_watermark_goes_stale(clean_session, monkeypatch):
    stale = datetime.now(timezone.utc) - FULL_SYNC_MAX_AGE - timedelta(minutes=1)
    assert _tick_mode(clean_session, monkeypatch, stale) == {"incremental": False}
