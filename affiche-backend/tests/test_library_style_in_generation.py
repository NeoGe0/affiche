from contextlib import contextmanager
from unittest.mock import MagicMock

import affiche.app.mediaserver.service.library_style as style_module
import affiche.app.mediaserver.service.media_server_poster_service as poster_module
from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.model.text_options import TextOptions
from affiche.app.mediaserver.library.model import LibraryItem
from affiche.app.mediaserver.service.media_server_poster_service import (
    GLOBAL_STYLE,
    LibraryPosterService,
    LibraryPosterStyle,
)

def _settings(**columns) -> MagicMock:
    return MagicMock(style_profile_id=None, **columns)

def _service_with_settings(settings, monkeypatch) -> LibraryPosterService:
    monkeypatch.setattr(style_module, "LibrarySettingsService",
                        lambda _session: MagicMock(get_settings=lambda _id: settings))
    return object.__new__(LibraryPosterService)

def test_no_settings_row_inherits_the_global_style(monkeypatch):
    svc = _service_with_settings(None, monkeypatch)

    assert svc._get_library_style(MagicMock(), 10) == GLOBAL_STYLE

def test_null_columns_inherit_the_global_style(monkeypatch):
    svc = _service_with_settings(_settings(overlay_options=None, text_options=None), monkeypatch)

    style = svc._get_library_style(MagicMock(), 10)

    assert style.overlay_options is None
    assert style.text_options is None

def test_stored_columns_are_parsed_into_options(monkeypatch):
    svc = _service_with_settings(_settings(
        overlay_options={"border_enabled": True, "border_px": 42},
        text_options={"font_color": "#FF0000"},
    ), monkeypatch)

    style = svc._get_library_style(MagicMock(), 10)

    assert style.overlay_options.border_px == 42
    assert style.text_options.font_color == "#FF0000"

def test_one_readable_column_does_not_drag_the_other_along(monkeypatch):
    svc = _service_with_settings(_settings(overlay_options={"border_px": 42}, text_options=None), monkeypatch)

    style = svc._get_library_style(MagicMock(), 10)

    assert style.overlay_options.border_px == 42
    assert style.text_options is None

def test_unreadable_stored_style_falls_back_instead_of_failing_the_run(monkeypatch):
    svc = _service_with_settings(_settings(
        overlay_options={"border_px": "not-a-number"},
        text_options={"gone_since": True},
    ), monkeypatch)

    style = svc._get_library_style(MagicMock(), 10)

    assert style == GLOBAL_STYLE

def _item() -> LibraryItem:
    return LibraryItem(id=1, library_id=10, external_id="x", title="T", type="movie")

def test_process_item_hands_the_library_style_to_the_poster_save(monkeypatch):
    style = LibraryPosterStyle(overlay_options=OverlayOptions(border_px=42),
                               text_options=TextOptions(font_color="#FF0000"))
    svc = object.__new__(LibraryPosterService)
    svc._session_factory = MagicMock()
    svc._resolver = MagicMock()
    svc._resolver.resolve_item_poster.return_value = MagicMock(source="http://p.jpg", styled=True,
                                                               provider="tmdb")
    svc._process_item_poster = MagicMock(return_value=True)

    @contextmanager
    def fake_scope(_session_factory=None):
        yield MagicMock(), MagicMock()

    monkeypatch.setattr(poster_module, "library_session", fake_scope)

    assert svc._process_item(_item(), "movie", "movie", ["tmdb"], MagicMock(), style,
                             MagicMock(), False) is True

    kwargs = svc._process_item_poster.call_args.kwargs
    assert kwargs["overlay_options"] is style.overlay_options
    assert kwargs["text_options"] is style.text_options

def _apply_service(monkeypatch, style) -> LibraryPosterService:
    svc = object.__new__(LibraryPosterService)
    svc._session_factory = MagicMock()
    svc._connector_factory = MagicMock()
    svc._get_library_style = MagicMock(return_value=style)
    svc._get_upload_enabled = MagicMock(return_value=False)
    svc._process_item_poster = MagicMock(return_value=True)

    repo = MagicMock()
    repo.get_library_item.return_value = _item()

    @contextmanager
    def fake_scope(_session_factory=None):
        yield repo, MagicMock()

    monkeypatch.setattr(poster_module, "library_session", fake_scope)
    return svc

def test_manual_apply_falls_back_to_the_library_style(monkeypatch):
    style = LibraryPosterStyle(overlay_options=OverlayOptions(border_px=42),
                               text_options=TextOptions(font_color="#FF0000"))
    svc = _apply_service(monkeypatch, style)

    svc.apply_poster(1, 10, 1, "http://p.jpg")

    kwargs = svc._process_item_poster.call_args.kwargs
    assert kwargs["overlay_options"] is style.overlay_options
    assert kwargs["text_options"] is style.text_options

def test_an_edited_style_still_wins_over_the_library_style(monkeypatch):
    edited = OverlayOptions(border_px=7)
    svc = _apply_service(monkeypatch, LibraryPosterStyle(
        overlay_options=OverlayOptions(border_px=42), text_options=TextOptions()))

    svc.apply_poster(1, 10, 1, "http://p.jpg", overlay_options=edited)

    assert svc._process_item_poster.call_args.kwargs["overlay_options"] is edited

def test_season_posters_get_the_same_style_as_the_show(monkeypatch):
    style = LibraryPosterStyle(overlay_options=OverlayOptions(border_px=42), text_options=None)
    svc = object.__new__(LibraryPosterService)
    svc._resolver = MagicMock()
    svc._resolver.resolve_season_poster.return_value = MagicMock(source="http://s.jpg", styled=True,
                                                                 provider="tmdb")
    svc._process_season_poster = MagicMock(return_value=True)
    season = MagicMock(season_number=1)

    assert svc._process_season(MagicMock(), MagicMock(), season, _item(), ["tmdb"], MagicMock(), style,
                               MagicMock(), False) is True

    kwargs = svc._process_season_poster.call_args.kwargs
    assert kwargs["overlay_options"] is style.overlay_options
    assert kwargs["text_options"] is style.text_options
