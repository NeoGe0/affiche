from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibrarySearch
from affiche.app.mediaserver.library.connector.alchemy_library_connector import AlchemyLibraryConnector
from affiche.external.plex.service.plex_service import PlexService
from affiche.external.jellyfin.service.jellyfin_service import JellyfinService
from affiche.config import Base
from affiche.app.mediaserver.library.model import LibraryItemSearch, SortDir

def test_plex_extracts_media_info_for_movie():
    media = SimpleNamespace(
        width=1920, height=1080, videoCodec='hevc', audioCodec='eac3', audioChannels=6,
        container='mkv', bitrate=8000,
        parts=[SimpleNamespace(size=123456789)],
    )
    item = SimpleNamespace(type='movie', title='Movie', media=[media])

    info = PlexService('http://x', 't')._extract_media_info(item)

    assert info == {
        'media_resolution': '1080p',
        'media_width': 1920,
        'media_height': 1080,
        'video_codec': 'hevc',
        'audio_codec': 'eac3',
        'audio_channels': 6,
        'media_container': 'mkv',
        'media_bitrate': 8_000_000,
        'media_size_bytes': 123456789,
    }

def test_plex_returns_all_none_for_show():
    item = SimpleNamespace(type='show', title='Show')
    info = PlexService('http://x', 't')._extract_media_info(item)
    assert set(info.values()) == {None}

def test_jellyfin_extracts_media_info_for_movie():
    item = {
        'Type': 'Movie', 'Name': 'Movie',
        'MediaSources': [{
            'Container': 'mkv', 'Size': 123456789, 'Bitrate': 8_000_000,
            'MediaStreams': [
                {'Type': 'Video', 'Width': 3840, 'Height': 2160, 'Codec': 'hevc'},
                {'Type': 'Audio', 'Codec': 'eac3', 'Channels': 6},
            ],
        }],
    }

    info = JellyfinService('http://x', 'k')._extract_media_info(item)

    assert info == {
        'media_resolution': '4K',
        'media_width': 3840,
        'media_height': 2160,
        'video_codec': 'hevc',
        'audio_codec': 'eac3',
        'audio_channels': 6,
        'media_container': 'mkv',
        'media_bitrate': 8_000_000,
        'media_size_bytes': 123456789,
    }

def test_jellyfin_returns_all_none_for_series():
    info = JellyfinService('http://x', 'k')._extract_media_info({'Type': 'Series', 'Name': 'Show'})
    assert set(info.values()) == {None}

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()

@pytest.fixture
def library_id(db) -> int:
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    db.flush()
    LibraryService(db).create(Library(
        media_server_id=server.id, external_id="lib-1", name="Movies",
        type="movie", language="en", enabled=True,
    ))
    db.commit()
    return LibraryService(db).find_libraries(LibrarySearch(media_server_id=server.id))[0].id

def test_media_fields_persist_and_refresh_on_reupsert(db, library_id):
    connector = AlchemyLibraryConnector(db)
    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id="m1", title="M", type="movie",
                    media_resolution="1080p", media_height=1080, media_width=1920,
                    video_codec="h264", media_size_bytes=5_000_000_000),
    ])

    stored = connector.find_items(LibraryItemSearch(library_id=library_id))[0]
    assert stored.media_resolution == "1080p"
    assert stored.media_height == 1080
    assert stored.video_codec == "h264"
    assert stored.media_size_bytes == 5_000_000_000

    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id="m1", title="M", type="movie",
                    media_resolution="4K", media_height=2160, media_width=3840,
                    video_codec="hevc", media_size_bytes=25_000_000_000),
    ])
    refreshed = connector.find_items(LibraryItemSearch(library_id=library_id))[0]
    assert refreshed.media_resolution == "4K"
    assert refreshed.media_height == 2160
    assert refreshed.video_codec == "hevc"
    assert refreshed.media_size_bytes == 25_000_000_000
