from unittest.mock import MagicMock

import pytest

from affiche.external.plex.service.plex_service import PlexService

def _poster(rating_key, key="/library/metadata/42/thumb/1700"):
    poster = MagicMock()
    poster.ratingKey = rating_key
    poster.key = key
    return poster

def _service(item):
    svc = object.__new__(PlexService)
    svc._plex = MagicMock()
    svc._plex.fetchItem.return_value = item
    svc._plex.url.side_effect = \
        lambda key, includeToken=None: f"http://plex:32400{key}?X-Plex-Token=tok"
    return svc

def _item(posters, poster_url="http://plex/photo/transcode?url=thumb-2"):
    item = MagicMock()
    item.title = "T"
    item.posters.return_value = posters
    item.posterUrl = poster_url
    return item

def test_reset_skips_uploaded_posters():
    item = _item([_poster("upload://posters/abc"), _poster("media://12/thumb")])
    svc = _service(item)

    assert svc.reset_poster("42").success is True
    item.setPoster.assert_called_once_with(item.posters.return_value[1])

def test_reset_returns_the_url_of_the_poster_it_selected():
    item = _item([_poster("media://12/thumb", key="/library/metadata/42/thumb/1700")])
    svc = _service(item)

    result = svc.reset_poster("42")

    assert result.poster_url == "http://plex:32400/library/metadata/42/thumb/1700?X-Plex-Token=tok"

def test_reset_keeps_an_absolute_poster_url_as_is():
    item = _item([_poster("media://12/thumb", key="https://metadata-static.plex.tv/a/b.jpg")])
    svc = _service(item)

    assert svc.reset_poster("42").poster_url == "https://metadata-static.plex.tv/a/b.jpg"

def test_reset_reports_no_url_when_the_poster_has_no_key():
    item = _item([_poster("media://12/thumb", key=None)])
    svc = _service(item)

    result = svc.reset_poster("42")

    assert result.success is True
    assert result.poster_url is None

def test_reset_fails_when_only_uploads_exist():
    item = _item([_poster("upload://posters/abc"), _poster("upload://posters/def")])
    svc = _service(item)

    assert svc.reset_poster("42").success is False
    item.setPoster.assert_not_called()

def test_reset_fails_when_no_posters_at_all():
    item = _item([])
    svc = _service(item)

    assert svc.reset_poster("42").success is False

def test_get_poster_url_reads_the_item_back():
    item = _item([], poster_url="http://plex/photo/transcode?url=thumb-9")
    svc = _service(item)

    assert svc.get_poster_url("42") == "http://plex/photo/transcode?url=thumb-9"

def test_get_poster_url_is_none_when_the_item_is_gone():
    from plexapi.exceptions import NotFound

    svc = object.__new__(PlexService)
    svc._plex = MagicMock()
    svc._plex.fetchItem.side_effect = NotFound("gone")

    assert svc.get_poster_url("42") is None
