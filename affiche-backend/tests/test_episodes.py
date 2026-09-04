from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import affiche.models
from affiche.config import Base
from affiche.app.mediaserver.connector.media_server_entity import MediaServerEntity
from affiche.app.mediaserver.library.connector.library_entity import LibraryEntity
from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity
from affiche.app.mediaserver.library.seasons.connector.library_season_entity import LibrarySeasonEntity
from affiche.app.mediaserver.library.episodes.library_episode_service import LibraryEpisodeService
from affiche.app.mediaserver.library.model import LibraryEpisode
from affiche.app.mediaserver.model.media_server import MediaServerType

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()

def _seed_show_season(session):
    ms = MediaServerEntity(name="P", type=MediaServerType.PLEX, url="u", token="t", enabled=True)
    session.add(ms); session.flush()
    lib = LibraryEntity(media_server_id=ms.id, external_id="1", name="TV", type="show",
                        language="en", enabled=True)
    session.add(lib); session.flush()
    show = LibraryItemEntity(external_id="900", library_id=lib.id, title="Show", type="show")
    session.add(show); session.flush()
    season = LibrarySeasonEntity(external_id="910", show_id=show.id, library_id=lib.id,
                                 season_number=1, title="Season 1", processed=False)
    session.add(season); session.flush()
    session.commit()
    return lib, show, season

def test_episodes_upsert_and_ordering(session):
    lib, show, season = _seed_show_season(session)
    svc = LibraryEpisodeService(session)

    svc.create_or_update([
        LibraryEpisode(external_id="e2", season_id=season.id, show_id=show.id, library_id=lib.id,
                       season_number=1, episode_number=2, title="Ep2", media_resolution="1080p"),
        LibraryEpisode(external_id="e1", season_id=season.id, show_id=show.id, library_id=lib.id,
                       season_number=1, episode_number=1, title="Ep1", media_resolution="4K"),
    ])
    eps = svc.get_season_episodes(season.id)
    assert [e.episode_number for e in eps] == [1, 2]
    assert eps[0].media_resolution == "4K"

def test_episodes_upsert_refreshes_quality(session):
    lib, show, season = _seed_show_season(session)
    svc = LibraryEpisodeService(session)
    svc.create_or_update([
        LibraryEpisode(external_id="e1", season_id=season.id, show_id=show.id, library_id=lib.id,
                       season_number=1, episode_number=1, title="Ep1", media_resolution="4K"),
    ])
    svc.create_or_update([
        LibraryEpisode(external_id="e1", season_id=season.id, show_id=show.id, library_id=lib.id,
                       season_number=1, episode_number=1, title="Ep1 v2", media_resolution="1080p"),
    ])
    eps = svc.get_season_episodes(season.id)
    assert len(eps) == 1
    assert eps[0].title == "Ep1 v2"
    assert eps[0].media_resolution == "1080p"

def test_plex_media_info_extracts_for_episode():
    from affiche.external.plex.service.plex_service import PlexService
    svc = PlexService.__new__(PlexService)
    part = SimpleNamespace(size=123456789)
    media = SimpleNamespace(width=1920, height=1080, videoCodec="hevc", audioCodec="eac3",
                            audioChannels=6, container="mkv", bitrate=8000, parts=[part])
    episode = SimpleNamespace(type="episode", media=[media], title="Ep")
    info = svc._extract_media_info(episode)
    assert info["media_resolution"] == "1080p"
    assert info["video_codec"] == "hevc"
    assert info["media_bitrate"] == 8000 * 1000
    assert info["media_size_bytes"] == 123456789
    show = SimpleNamespace(type="show", title="S")
    assert all(v is None for v in svc._extract_media_info(show).values())

def test_jellyfin_media_info_extracts_for_episode():
    from affiche.external.jellyfin.service.jellyfin_service import JellyfinService
    svc = JellyfinService.__new__(JellyfinService)
    item = {
        "Type": "Episode",
        "MediaSources": [{
            "Container": "mkv", "Bitrate": 8000000, "Size": 555,
            "MediaStreams": [
                {"Type": "Video", "Width": 3840, "Height": 2160, "Codec": "hevc"},
                {"Type": "Audio", "Codec": "eac3", "Channels": 6},
            ],
        }],
    }
    info = svc._extract_media_info(item)
    assert info["media_resolution"] == "4K"
    assert info["video_codec"] == "hevc"
    assert info["audio_channels"] == 6
    assert info["media_size_bytes"] == 555
    assert all(v is None for v in svc._extract_media_info({"Type": "Series"}).values())

def test_track_episodes_setting_round_trip(session):
    from affiche.app.mediaserver.library.settings.connector.alchemy_library_settings_connector import (
        AlchemyLibrarySettingsConnector,
    )
    from affiche.app.mediaserver.library.settings.model.library_settings import LibrarySettings
    lib, _, _ = _seed_show_season(session)
    conn = AlchemyLibrarySettingsConnector(session)
    saved = conn.upsert(LibrarySettings(library_id=lib.id, track_episodes=True))
    assert saved.track_episodes is True
    assert conn.get(lib.id).track_episodes is True
