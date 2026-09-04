from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import affiche.api.routers.library  # noqa: F401  (warm the api package before service imports; avoids a media_server_service <-> api import cycle)
from affiche.app.mediaserver.service.plex_sync_service import PlexSynchronisationService
from affiche.app.mediaserver.library.sync.media_server_synchronisation_service import (
    MediaServerSynchronisationService,
)
from affiche.app.mediaserver.model.media_server import MediaServerType
from affiche.config.exceptions.exceptions import ItemMissingOnMediaServerException
from affiche.external.plex.model.models import PlexLibraryItem
from affiche.external.plex.service.plex_service import PlexService

def _svc_with_connector(library_service):
    fake_plex = MagicMock(spec=PlexService)
    connector_factory = MagicMock()
    connector_factory.get.return_value = fake_plex
    svc = PlexSynchronisationService(library_service, MagicMock(), MagicMock(), MagicMock(),
                                     MagicMock(), MagicMock(), connector_factory)
    return svc, fake_plex, connector_factory

def _fetched_movie() -> PlexLibraryItem:
    return PlexLibraryItem(
        id="500", library_id="10", title="New Title", type="movie", year=2021,
        added_at=datetime(2021, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2021, 1, 2, tzinfo=timezone.utc),
        tmdb_id="42", media_resolution="1080p", media_height=1080, video_codec="hevc",
    )

def test_sync_plex_item_upserts_fetched_metadata():
    library = SimpleNamespace(id=1, external_id="10")
    db_item = SimpleNamespace(external_id="500", title="Old Title")

    library_service = MagicMock()
    library_service.get_library.return_value = library
    library_service.get_library_item.side_effect = [db_item, SimpleNamespace(title="New Title")]

    svc, fake_plex, connector_factory = _svc_with_connector(library_service)
    fake_plex.get_library_item.return_value = _fetched_movie()

    media_server = SimpleNamespace(id=1, url="http://x", token="t")
    result = svc.sync_plex_item(media_server, 1, 500)

    connector_factory.get.assert_called_once_with(1)
    fake_plex.get_library_item.assert_called_once_with("500")
    upserted = library_service.create_or_update_items_batch.call_args[0][0]
    assert len(upserted) == 1
    item = upserted[0]
    assert item.library_id == 1
    assert item.title == "New Title"
    assert item.tmdb_id == 42
    assert item.media_resolution == "1080p"
    assert item.video_codec == "hevc"
    assert item.last_seen_at is not None
    assert result.title == "New Title"

def test_sync_plex_item_returns_none_when_missing_on_server():
    library_service = MagicMock()
    library_service.get_library.return_value = SimpleNamespace(id=1, external_id="10")
    library_service.get_library_item.return_value = SimpleNamespace(external_id="500", title="Old")

    svc, fake_plex, _ = _svc_with_connector(library_service)
    fake_plex.get_library_item.return_value = None

    result = svc.sync_plex_item(SimpleNamespace(id=1, url="u", token="t"), 1, 500)

    assert result is None
    library_service.create_or_update_items_batch.assert_not_called()

def test_sync_item_dispatches_by_server_type():
    media_server_service = MagicMock()
    media_server_service.get.return_value = SimpleNamespace(type=MediaServerType.PLEX)
    plex = MagicMock()
    jellyfin = MagicMock()
    session = MagicMock()
    svc = MediaServerSynchronisationService(session, media_server_service, plex, jellyfin)

    svc.sync_item(1, 2, 3)

    plex.sync_plex_item.assert_called_once()
    jellyfin.sync_jellyfin_item.assert_not_called()
    session.commit.assert_called_once()

def test_sync_item_reports_an_item_that_is_gone_upstream():
    media_server_service = MagicMock()
    media_server_service.get.return_value = SimpleNamespace(type=MediaServerType.PLEX)
    plex = MagicMock()
    plex.sync_plex_item.return_value = None
    session = MagicMock()
    svc = MediaServerSynchronisationService(session, media_server_service, plex, MagicMock())

    with pytest.raises(ItemMissingOnMediaServerException) as raised:
        svc.sync_item(1, 2, 3)

    assert "not found on the media server" in raised.value.message
    session.commit.assert_not_called()
