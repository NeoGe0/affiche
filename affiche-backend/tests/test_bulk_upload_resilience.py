from contextlib import contextmanager
from unittest.mock import MagicMock

import affiche.app.mediaserver.service.poster_uploader as uploader_module
from affiche.app.mediaserver.library.model import Library, LibraryItem
from affiche.app.mediaserver.service.poster_uploader import PosterUploader

ITEM_COUNT = 6
DOOMED_ID = 3

def _library() -> Library:
    return Library(id=1, media_server_id=1, external_id="sec-1", name="Movies",
                   type="movie", language="en", enabled=True)

def _items() -> list[LibraryItem]:
    return [LibraryItem(id=i, library_id=1, external_id=f"x{i}", title=f"Movie {i}",
                        type="movie", processed=True)
            for i in range(ITEM_COUNT)]

def _uploader(monkeypatch, repo, upload_side_effect) -> PosterUploader:
    @contextmanager
    def _scope(_session_factory=None):
        yield repo, MagicMock()

    monkeypatch.setattr(uploader_module, "library_session", _scope)
    uploader = PosterUploader(file_store=MagicMock(), session_factory=MagicMock())
    uploader.upload_existing_item_poster = upload_side_effect
    return uploader

def test_a_raising_item_does_not_abandon_the_rest(monkeypatch, caplog):
    repo = MagicMock()
    repo.find_items.return_value = _items()
    attempted = []

    def upload(item, connector):
        attempted.append(item.id)
        if item.id == DOOMED_ID:
            raise OSError("stored poster vanished mid-run")
        return True

    uploader = _uploader(monkeypatch, repo, upload)

    uploader.upload_library_posters(_library(), connector=MagicMock())

    assert sorted(attempted) == list(range(ITEM_COUNT)), "every item should still be attempted"

def test_the_run_reports_the_failure_rather_than_swallowing_it(monkeypatch, caplog):
    repo = MagicMock()
    repo.find_items.return_value = _items()

    def upload(item, connector):
        if item.id == DOOMED_ID:
            raise OSError("stored poster vanished mid-run")
        return True

    uploader = _uploader(monkeypatch, repo, upload)

    with caplog.at_level("INFO"):
        uploader.upload_library_posters(_library(), connector=MagicMock())

    assert "stored poster vanished mid-run" in caplog.text, "the cause should be logged"
    assert f"{ITEM_COUNT - 1} uploaded, 1 failed" in caplog.text

def test_a_clean_run_still_counts_every_item(monkeypatch, caplog):
    repo = MagicMock()
    repo.find_items.return_value = _items()
    uploader = _uploader(monkeypatch, repo, lambda item, connector: True)

    with caplog.at_level("INFO"):
        uploader.upload_library_posters(_library(), connector=MagicMock())

    assert f"{ITEM_COUNT} uploaded, 0 failed" in caplog.text

def test_a_falsy_result_is_still_counted_failed_not_raised(monkeypatch, caplog):
    repo = MagicMock()
    repo.find_items.return_value = _items()
    uploader = _uploader(monkeypatch, repo, lambda item, connector: item.id != DOOMED_ID)

    with caplog.at_level("INFO"):
        uploader.upload_library_posters(_library(), connector=MagicMock())

    assert f"{ITEM_COUNT - 1} uploaded, 1 failed" in caplog.text
