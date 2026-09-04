import pytest

from affiche.app.filestore.filestore import FileStoreService

SERVER_ART = b"the media server's own poster"
GENERATED = b"the poster affiche generated"

@pytest.fixture
def store(tmp_path) -> FileStoreService:
    return FileStoreService(root_dir=tmp_path)

def test_nothing_to_preserve_when_no_poster_is_stored(store):
    assert store.preserve_source(1, 42) is False
    assert store.source_version(1, 42) is None

def test_preserves_what_is_stored_before_generation_overwrites_it(store):
    store.save(1, 42, SERVER_ART)

    assert store.preserve_source(1, 42) is True
    store.save(1, 42, GENERATED)

    assert store.fetch(1, 42) == GENERATED
    assert store.fetch_source(1, 42) == SERVER_ART

def test_a_second_preserve_does_not_overwrite_the_original(store):
    store.save(1, 42, SERVER_ART)
    store.preserve_source(1, 42)
    store.save(1, 42, GENERATED)

    assert store.preserve_source(1, 42) is False
    assert store.fetch_source(1, 42) == SERVER_ART

def test_the_source_keeps_its_own_version(store):
    store.save(1, 42, SERVER_ART)
    store.preserve_source(1, 42)
    source_version = store.source_version(1, 42)

    store.save(1, 42, GENERATED)

    assert store.source_version(1, 42) == source_version
    assert store.version(1, 42) != source_version

def test_deleting_the_poster_drops_the_preserved_source(store):
    store.save(1, 42, SERVER_ART)
    store.preserve_source(1, 42)
    store.save(1, 42, GENERATED)

    store.delete(1, 42)

    assert store.source_version(1, 42) is None
    with pytest.raises(FileNotFoundError):
        store.fetch_source(1, 42)

def test_seasons_preserve_their_own_source(store):
    store.save(1, 42, SERVER_ART, season_number=1)
    store.save(1, 42, b"other season", season_number=2)

    store.preserve_source(1, 42, season_number=1)
    store.save(1, 42, GENERATED, season_number=1)

    assert store.fetch_source(1, 42, season_number=1) == SERVER_ART
    assert store.source_version(1, 42, season_number=2) is None

def test_the_source_copy_survives_a_library_wide_thumbnail_rebuild(store, tmp_path):
    sized = FileStoreService(root_dir=tmp_path / "b", thumbnailer=lambda data: b"thumb:" + data)
    sized.save(1, 42, SERVER_ART)
    sized.preserve_source(1, 42)
    sized.save(1, 42, GENERATED)

    assert sized.fetch_thumbnail(1, 42) == b"thumb:" + GENERATED
    assert sized.fetch_source(1, 42) == SERVER_ART

def _service(store):
    from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
    service = object.__new__(LibraryPosterService)
    service._file_store = store
    return service

def _item(**overrides):
    from affiche.app.mediaserver.library.model import LibraryItem
    fields = dict(id=42, library_id=1, external_id="x", title="T", type="movie", processed=False)
    fields.update(overrides)
    return LibraryItem(**fields)

def test_the_service_preserves_for_an_unprocessed_item(store):
    store.save(1, 42, SERVER_ART)

    _service(store)._preserve_source(_item(processed=False))

    assert store.fetch_source(1, 42) == SERVER_ART

def test_the_service_refuses_once_the_item_is_processed(store):
    store.save(1, 42, GENERATED)

    _service(store)._preserve_source(_item(processed=True))

    assert store.source_version(1, 42) is None
