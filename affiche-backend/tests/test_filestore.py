import hashlib

from affiche.app.filestore.filestore import FileStoreService, poster_digest

def _store(tmp_path) -> FileStoreService:
    return FileStoreService(root_dir=tmp_path)

def test_poster_digest_is_sha256_of_the_bytes():
    assert poster_digest(b"poster") == hashlib.sha256(b"poster").hexdigest()

def test_digest_round_trips_a_saved_poster(tmp_path):
    store = _store(tmp_path)
    store.save(1, 42, b"poster")

    assert store.digest(1, 42) == poster_digest(b"poster")

def test_digest_changes_when_the_poster_is_overwritten(tmp_path):
    store = _store(tmp_path)
    store.save(1, 42, b"poster")
    before = store.digest(1, 42)
    store.save(1, 42, b"different poster")

    assert store.digest(1, 42) != before

def test_digest_is_none_when_nothing_is_stored(tmp_path):
    assert _store(tmp_path).digest(1, 42) is None

def test_season_posters_have_their_own_digest(tmp_path):
    store = _store(tmp_path)
    store.save(1, 42, b"show poster")
    store.save(1, 42, b"season poster", season_number=1)

    assert store.digest(1, 42, season_number=1) == poster_digest(b"season poster")
    assert store.digest(1, 42) == poster_digest(b"show poster")
    assert store.digest(1, 42, season_number=2) is None
