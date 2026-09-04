from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module
from affiche.app.provider_stats import (
    RETENTION_DAYS,
    ProviderStatsQuery,
    ProviderStatsService,
)
from affiche.app.provider_stats.connector.provider_hit_entity import ProviderHitEntity
from affiche.config import Base
from affiche.config.database import SessionLocal

TODAY = date.today()

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(autoflush=False, bind=engine)()
    yield session
    session.close()
    engine.dispose()

@pytest.fixture
def stats(db):
    return ProviderStatsService(db)

def _record(stats, db, provider, library_id=1, day=None, times=1):
    for _ in range(times):
        stats.record(provider, library_id, day=day)
    db.commit()

class TestCounting:

    def test_a_stored_poster_is_counted_against_its_provider(self, stats, db):
        _record(stats, db, "tmdb")

        assert stats.totals(ProviderStatsQuery()) == {"tmdb": 1}

    def test_repeated_hits_accumulate_into_one_row_per_day(self, stats, db):
        _record(stats, db, "tmdb", times=5)

        assert stats.totals(ProviderStatsQuery()) == {"tmdb": 5}
        assert db.query(ProviderHitEntity).count() == 1

    def test_a_second_hit_in_one_uncommitted_transaction_updates_the_first(self, stats, db):
        stats.record("tmdb", 1)
        stats.record("tmdb", 1)
        db.commit()

        assert db.query(ProviderHitEntity).count() == 1
        assert stats.totals(ProviderStatsQuery()) == {"tmdb": 2}

    def test_providers_are_counted_separately(self, stats, db):
        _record(stats, db, "tmdb", times=2)
        _record(stats, db, "fanart")

        assert stats.totals(ProviderStatsQuery()) == {"tmdb": 2, "fanart": 1}

    def test_libraries_are_counted_separately(self, stats, db):
        _record(stats, db, "tmdb", library_id=1)
        _record(stats, db, "tmdb", library_id=2)

        assert db.query(ProviderHitEntity).count() == 2
        assert stats.totals(ProviderStatsQuery()) == {"tmdb": 2}
        assert stats.totals(ProviderStatsQuery(library_id=2)) == {"tmdb": 1}

    def test_days_are_counted_separately(self, stats, db):
        _record(stats, db, "tmdb", day=TODAY - timedelta(days=1))
        _record(stats, db, "tmdb", day=TODAY)

        assert [(row.day, row.count) for row in stats.daily(ProviderStatsQuery())] == [
            (TODAY - timedelta(days=1), 1), (TODAY, 1),
        ]

    def test_the_server_fallback_is_counted_too(self, stats, db):
        _record(stats, db, "server", times=3)
        _record(stats, db, "manual")

        assert stats.totals(ProviderStatsQuery()) == {"server": 3, "manual": 1}

    def test_a_poster_with_no_provider_is_not_counted(self, stats, db):
        _record(stats, db, None)
        _record(stats, db, "")

        assert stats.totals(ProviderStatsQuery()) == {}
        assert db.query(ProviderHitEntity).count() == 0

    def test_recording_does_not_commit_on_its_own(self, stats, db):
        stats.record("tmdb", 1)
        db.rollback()

        assert stats.totals(ProviderStatsQuery()) == {}

    def test_recording_never_raises(self, db):
        broken = ProviderStatsService(MagicMock(**{"execute.side_effect": RuntimeError("db gone")}))

        broken.record("tmdb", 1)

class TestWindows:

    def test_the_window_includes_today(self, stats, db):
        _record(stats, db, "tmdb")

        assert stats.totals(ProviderStatsQuery(days=1)) == {"tmdb": 1}

    def test_a_day_outside_the_window_is_excluded(self, stats, db):
        _record(stats, db, "tmdb", day=TODAY - timedelta(days=10))
        _record(stats, db, "fanart")

        assert stats.totals(ProviderStatsQuery(days=7)) == {"fanart": 1}

    def test_the_series_is_summed_across_libraries(self, stats, db):
        _record(stats, db, "tmdb", library_id=1, times=2)
        _record(stats, db, "tmdb", library_id=2, times=3)

        assert [(row.provider, row.count) for row in stats.daily(ProviderStatsQuery())] == [("tmdb", 5)]

    def test_the_series_can_be_narrowed_to_one_library(self, stats, db):
        _record(stats, db, "tmdb", library_id=1, times=2)
        _record(stats, db, "tmdb", library_id=2, times=3)

        assert [(row.provider, row.count) for row in stats.daily(ProviderStatsQuery(library_id=2))] == [("tmdb", 3)]

    def test_a_quiet_day_is_absent_rather_than_zero(self, stats, db):
        _record(stats, db, "tmdb", day=TODAY - timedelta(days=2))
        _record(stats, db, "tmdb", day=TODAY)

        assert len(stats.daily(ProviderStatsQuery(days=7))) == 2

class TestRetention:

    def test_tallies_past_the_retention_window_are_dropped(self, stats, db):
        old = TODAY - timedelta(days=RETENTION_DAYS + 5)
        db.add(ProviderHitEntity(day=old, provider="tmdb", library_id=1, count=9))
        db.commit()

        _record(stats, db, "fanart")

        assert db.query(ProviderHitEntity).filter(ProviderHitEntity.day == old).count() == 0

    def test_tallies_inside_the_window_survive(self, stats, db):
        recent = TODAY - timedelta(days=30)
        db.add(ProviderHitEntity(day=recent, provider="tmdb", library_id=1, count=9))
        db.commit()

        _record(stats, db, "fanart")

        assert db.query(ProviderHitEntity).filter(ProviderHitEntity.day == recent).count() == 1

    def test_incrementing_an_existing_tally_does_not_sweep(self, stats, db):
        _record(stats, db, "tmdb")
        old = TODAY - timedelta(days=RETENTION_DAYS + 5)
        db.add(ProviderHitEntity(day=old, provider="fanart", library_id=1, count=9))
        db.commit()

        _record(stats, db, "tmdb")

        assert db.query(ProviderHitEntity).filter(ProviderHitEntity.day == old).count() == 1

class TestEndpoint:

    def test_the_history_endpoint_serves_the_series_and_the_totals(self, authenticated_app):
        with TestClient(authenticated_app) as client:
            session = SessionLocal()
            try:
                stats = ProviderStatsService(session)
                stats.record("tmdb", 4242)
                stats.record("tmdb", 4242)
                stats.record("fanart", 4242)
                session.commit()
            finally:
                session.close()

            resp = client.get("/affiche/dashboard/provider-history",
                              params={"days": 7, "library_id": 4242})

        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == 7
        assert body["totals"] == [{"provider": "tmdb", "count": 2},
                                  {"provider": "fanart", "count": 1}]
        assert {row["provider"] for row in body["series"]} == {"tmdb", "fanart"}
        assert body["series"][0]["day"] == TODAY.isoformat()

    def test_totals_rank_the_providers(self, authenticated_app):
        with TestClient(authenticated_app) as client:
            session = SessionLocal()
            try:
                stats = ProviderStatsService(session)
                for _ in range(3):
                    stats.record("fanart", 4243)
                stats.record("tmdb", 4243)
                session.commit()
            finally:
                session.close()

            resp = client.get("/affiche/dashboard/provider-history", params={"library_id": 4243})

        assert [row["provider"] for row in resp.json()["totals"]] == ["fanart", "tmdb"]

    def test_an_install_that_has_generated_nothing_answers_empty(self, authenticated_app):
        with TestClient(authenticated_app) as client:
            resp = client.get("/affiche/dashboard/provider-history", params={"library_id": 999999})

        assert resp.status_code == 200
        assert resp.json()["series"] == []
        assert resp.json()["totals"] == []

    def test_a_window_longer_than_retention_is_refused(self, authenticated_app):
        with TestClient(authenticated_app) as client:
            resp = client.get("/affiche/dashboard/provider-history",
                              params={"days": RETENTION_DAYS + 1})

        assert resp.status_code == 422

    def test_the_endpoint_is_session_gated(self):
        with TestClient(main_module.app) as client:
            assert client.get("/affiche/dashboard/provider-history").status_code == 401
