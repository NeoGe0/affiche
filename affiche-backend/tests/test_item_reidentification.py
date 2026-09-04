from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.sync.reidentification import (
    RemoteIdentity,
    match_readded_items,
    match_readded_seasons,
    match_split_items,
)
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

class _Row:

    def __init__(self, id, external_id, type="movie", imdb_id=None, tmdb_id=None, tvdb_id=None):
        self.id = id
        self.external_id = external_id
        self.type = type
        self.imdb_id = imdb_id
        self.tmdb_id = tmdb_id
        self.tvdb_id = tvdb_id

class _Season:
    def __init__(self, id, external_id, season_number):
        self.id = id
        self.external_id = external_id
        self.season_number = season_number

class TestMatching:
    def test_pairs_a_departing_row_with_the_id_it_came_back_under(self):
        existing = [_Row(1, "100", tmdb_id="603")]
        incoming = [RemoteIdentity(external_id="900", type="movie", tmdb_id="603")]

        assert match_readded_items(existing, incoming) == {1: "900"}

    def test_matches_across_the_types_the_two_sides_store_ids_as(self):
        existing = [_Row(1, "100", tmdb_id=603)]
        incoming = [RemoteIdentity(external_id="900", type="movie", tmdb_id="603")]

        assert match_readded_items(existing, incoming) == {1: "900"}

    def test_leaves_an_item_the_server_still_lists_alone(self):
        existing = [_Row(1, "100", tmdb_id="603")]
        incoming = [
            RemoteIdentity(external_id="100", type="movie", tmdb_id="603"),
            RemoteIdentity(external_id="900", type="movie", tmdb_id="603"),
        ]

        assert match_readded_items(existing, incoming) == {}

    def test_refuses_an_ambiguous_pairing(self):
        existing = [_Row(1, "100", tmdb_id="603"), _Row(2, "101", tmdb_id="603")]
        incoming = [RemoteIdentity(external_id="900", type="movie", tmdb_id="603")]

        assert match_readded_items(existing, incoming) == {}

    def test_does_not_pair_across_types(self):
        existing = [_Row(1, "100", type="movie", tvdb_id="81189")]
        incoming = [RemoteIdentity(external_id="900", type="show", tvdb_id="81189")]

        assert match_readded_items(existing, incoming) == {}

    def test_ignores_rows_with_no_guid_at_all(self):
        existing = [_Row(1, "100")]
        incoming = [RemoteIdentity(external_id="900", type="movie")]

        assert match_readded_items(existing, incoming) == {}

    def test_a_split_is_the_same_pairing_after_the_fact(self):
        existing = [_Row(1, "100", tmdb_id="603"), _Row(2, "900", tmdb_id="603")]
        incoming = [RemoteIdentity(external_id="900", type="movie", tmdb_id="603")]

        assert match_readded_items(existing, incoming) == {}
        assert [(s.stale_id, s.fresh_id, s.external_id) for s in
                match_split_items(existing, incoming)] == [(1, 2, "900")]

    def test_no_split_while_both_rows_are_still_listed(self):
        existing = [_Row(1, "100", tmdb_id="603"), _Row(2, "900", tmdb_id="603")]
        incoming = [
            RemoteIdentity(external_id="100", type="movie", tmdb_id="603"),
            RemoteIdentity(external_id="900", type="movie", tmdb_id="603"),
        ]

        assert match_split_items(existing, incoming) == []

    def test_seasons_pair_on_their_number(self):
        existing = [_Season(10, "200", 1), _Season(11, "201", 2)]

        assert match_readded_seasons(existing, {1: "900", 2: "901"}) == {10: "900", 11: "901"}

    def test_seasons_already_holding_the_new_id_are_left_alone(self):
        existing = [_Season(10, "900", 1)]

        assert match_readded_seasons(existing, {1: "900"}) == {}

@pytest.fixture
def library(session: Session):
    server = MediaServerPersistenceConnector(session).create(MediaServer(
        name="Plex", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    session.flush()
    service = LibraryService(session)
    service.create(Library(media_server_id=server.id, external_id="lib-1", name="Movies",
                           type="movie", language="en", enabled=True))
    session.flush()
    return service.find_libraries(LibrarySearch(media_server_id=server.id))[0]

def _only_item(service, library_id) -> LibraryItem:
    items = service.find_items(LibraryItemSearch(library_id=library_id, deleted=None))
    assert len(items) == 1, "the row must be adopted, not duplicated"
    return items[0]

class TestAdoption:
    def test_the_row_survives_the_move_and_stays_out_of_the_trash(self, session: Session, library):
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="100", title="Alien", type="movie",
            tmdb_id="348", last_seen_at=T0,
        )])
        session.flush()
        original = _only_item(service, library.id)
        original.processed = True
        original.locked = True
        original.poster_hash = "digest-of-what-plex-holds"
        original.poster_uploaded_at = T0
        service.library_repo.create_or_update_item(original)

        t1 = T0 + timedelta(hours=1)
        adopted, _ = service.adopt_readded_items(library.id, [
            RemoteIdentity(external_id="900", type="movie", tmdb_id="348"),
        ])
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="900", title="Alien", type="movie",
            tmdb_id="348", last_seen_at=t1,
        )])
        session.flush()
        soft_deleted, _ = service.reconcile_deletions(library.id, t1)
        session.expire_all()

        assert adopted == 1
        assert soft_deleted == 0
        item = _only_item(service, library.id)
        assert item.id == original.id, "same row, so the stored poster still belongs to it"
        assert item.external_id == "900"
        assert item.deleted_at is None
        assert item.processed is True
        assert item.locked is True
        assert item.poster_hash is None
        assert item.poster_uploaded_at is None

    def test_a_row_already_in_the_trash_is_rescued(self, session: Session, library):
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="100", title="Alien", type="movie",
            tmdb_id="348", last_seen_at=T0,
        )])
        session.flush()
        service.reconcile_deletions(library.id, T0 + timedelta(hours=1))
        session.expire_all()
        trashed = _only_item(service, library.id)
        assert trashed.deleted_at is not None

        t2 = T0 + timedelta(hours=2)
        assert service.adopt_readded_items(library.id, [
            RemoteIdentity(external_id="900", type="movie", tmdb_id="348"),
        ]) == (1, 0)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="900", title="Alien", type="movie",
            tmdb_id="348", last_seen_at=t2,
        )])
        session.flush()
        _, restored = service.reconcile_deletions(library.id, t2)
        session.expire_all()

        assert restored == 1
        assert _only_item(service, library.id).deleted_at is None

class TestMerging:

    def _split(self, session, library, **fresh_state):
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="100", title="Backrooms", type="movie",
            tmdb_id="348", last_seen_at=T0,
        )])
        session.flush()
        stale = service.find_items(LibraryItemSearch(library_id=library.id))[0]
        stale.processed = True
        stale.poster_provider = "tmdb"
        service.library_repo.create_or_update_item(stale)

        t1 = T0 + timedelta(hours=1)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="900", title="Backrooms", type="movie",
            tmdb_id="348", last_seen_at=t1,
        )])
        session.flush()
        service.reconcile_deletions(library.id, t1)
        session.expire_all()

        fresh = next(i for i in service.find_items(LibraryItemSearch(library_id=library.id))
                     if i.external_id == "900")
        if fresh_state:
            for field, value in fresh_state.items():
                setattr(fresh, field, value)
            service.library_repo.create_or_update_item(fresh)
        return service, stale, fresh

    def test_the_two_rows_become_one_again(self, session: Session, library):
        service, stale, fresh = self._split(session, library)
        assert stale.id != fresh.id

        t2 = T0 + timedelta(hours=2)
        adopted, merged = service.adopt_readded_items(library.id, [
            RemoteIdentity(external_id="900", type="movie", tmdb_id="348"),
        ])
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="900", title="Backrooms", type="movie",
            tmdb_id="348", last_seen_at=t2,
        )])
        session.flush()
        service.reconcile_deletions(library.id, t2)
        session.expire_all()

        assert (adopted, merged) == (0, 1)
        item = _only_item(service, library.id)
        assert item.id == stale.id
        assert item.external_id == "900"
        assert item.deleted_at is None
        assert item.processed is True
        assert item.poster_provider == "tmdb"

    def test_a_second_row_with_work_of_its_own_is_left_alone(self, session: Session, library):
        service, stale, fresh = self._split(session, library, processed=True)

        assert service.adopt_readded_items(library.id, [
            RemoteIdentity(external_id="900", type="movie", tmdb_id="348"),
        ]) == (0, 0)
        session.expire_all()

        rows = service.find_items(LibraryItemSearch(library_id=library.id, deleted=None))
        assert {row.id for row in rows} == {stale.id, fresh.id}

class TestPerItemMerge:

    def _split(self, session, library):
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="100", title="Backrooms", type="movie",
            tmdb_id="348", last_seen_at=T0,
        )])
        session.flush()
        stale = service.find_items(LibraryItemSearch(library_id=library.id))[0]
        stale.processed = True
        service.library_repo.create_or_update_item(stale)

        t1 = T0 + timedelta(hours=1)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="900", title="Backrooms", type="movie",
            tmdb_id="348", last_seen_at=t1,
        )])
        session.flush()
        service.reconcile_deletions(library.id, t1)
        session.expire_all()
        return service, stale

    def test_the_older_row_survives_and_leaves_the_trash(self, session: Session, library):
        service, stale = self._split(session, library)

        survivor = service.merge_readded_twin(
            library.id,
            RemoteIdentity(external_id="900", type="movie", tmdb_id="348"),
            is_gone=lambda external_id: external_id == "100",
        )
        session.expire_all()

        assert survivor == stale.id
        item = _only_item(service, library.id)
        assert item.id == stale.id
        assert item.external_id == "900"
        assert item.deleted_at is None
        assert item.processed is True

    def test_a_twin_the_server_still_holds_is_a_duplicate_not_a_move(self, session: Session, library):
        service, stale = self._split(session, library)

        survivor = service.merge_readded_twin(
            library.id,
            RemoteIdentity(external_id="900", type="movie", tmdb_id="348"),
            is_gone=lambda _external_id: False,
        )
        session.expire_all()

        assert survivor is None
        assert len(service.find_items(LibraryItemSearch(library_id=library.id, deleted=None))) == 2

    def test_an_item_with_no_twin_is_left_exactly_as_it_is(self, session: Session, library):
        service = LibraryService(session)
        service.create_or_update_items_batch([LibraryItem(
            library_id=library.id, external_id="900", title="Backrooms", type="movie",
            tmdb_id="348", last_seen_at=T0,
        )])
        session.flush()

        looked_up = []
        assert service.merge_readded_twin(
            library.id,
            RemoteIdentity(external_id="900", type="movie", tmdb_id="348"),
            is_gone=lambda external_id: looked_up.append(external_id) or True,
        ) is None
        assert looked_up == []
