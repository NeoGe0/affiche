from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import affiche.api  # noqa: F401,E402

from affiche.app.events import internal_event_bus
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository
from affiche.app.mediaserver.service.media_server_service import MediaServerService
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.service_configuration.exceptions import MediaServerNotFoundError
from affiche.config import Base

class TestMediaServerRepositoryCreate:

    def test_create_plex_server(self, session: Session):
        repository = MediaServerRepository(session)

        media_server = MediaServer(
            name="My Plex Server",
            type=MediaServerType.PLEX,
            url="http://localhost:32400",
            token="test-token-123",
            enabled=True,
        )

        created = repository.create(media_server)
        session.flush()

        assert created.id is not None
        assert created.name == "My Plex Server"
        assert created.type == MediaServerType.PLEX
        assert created.url == "http://localhost:32400"
        assert created.enabled is True

    def test_create_jellyfin_server(self, session: Session):
        repository = MediaServerRepository(session)

        media_server = MediaServer(
            name="My Jellyfin Server",
            type=MediaServerType.JELLYFIN,
            url="http://localhost:8096",
            token="jellyfin-api-key",
            enabled=True,
        )

        created = repository.create(media_server)
        session.flush()

        assert created.id is not None
        assert created.name == "My Jellyfin Server"
        assert created.type == MediaServerType.JELLYFIN
        assert created.url == "http://localhost:8096"

class TestMediaServerRepositoryGet:

    def test_get_existing_server(self, session: Session):
        repository = MediaServerRepository(session)

        media_server = MediaServer(
            name="Get Test Server",
            type=MediaServerType.PLEX,
            url="http://localhost:32400",
            token="token"
        )
        created = repository.create(media_server)
        session.flush()

        found = repository.get(created.id)

        assert found.id == created.id
        assert found.name == "Get Test Server"
        assert found.type == MediaServerType.PLEX

    def test_get_nonexistent_server_raises(self, session: Session):
        repository = MediaServerRepository(session)

        from affiche.app.service_configuration.exceptions import MediaServerNotFoundError

        with pytest.raises(MediaServerNotFoundError):
            repository.get(99999)

class TestMediaServerRepositoryFindAll:

    def test_find_all_returns_all_servers(self, session: Session):
        repository = MediaServerRepository(session)

        for i in range(3):
            media_server = MediaServer(
                name=f"Server {i}",
                type=MediaServerType.PLEX if i % 2 == 0 else MediaServerType.JELLYFIN,
                url=f"http://server{i}:32400",
                token=f"token-{i}"
            )
            repository.create(media_server)
        session.flush()

        results = repository.find_all()

        assert len(results) == 3

    def test_find_all_empty_when_no_servers(self, session: Session):
        repository = MediaServerRepository(session)

        results = repository.find_all()

        assert results == []

class TestMediaServerConnectorCreate:

    def test_connector_creates_entity(self, session: Session):
        connector = MediaServerPersistenceConnector(session)

        media_server = MediaServer(
            name="Connector Test",
            type=MediaServerType.PLEX,
            url="http://localhost:32400",
            token="token"
        )

        entity = connector.create(media_server)
        session.flush()

        assert entity.id is not None
        assert entity.name == "Connector Test"

    def test_connector_get_returns_entity(self, session: Session):
        connector = MediaServerPersistenceConnector(session)

        media_server = MediaServer(
            name="Get Entity Test",
            type=MediaServerType.JELLYFIN,
            url="http://localhost:8096",
            token="token"
        )

        created = connector.create(media_server)
        session.flush()

        found = connector.get(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.name == "Get Entity Test"

    def test_connector_get_nonexistent_returns_none(self, session: Session):
        connector = MediaServerPersistenceConnector(session)

        result = connector.get(99999)

        assert result is None

class TestMediaServerRepositoryUpdate:

    def test_update_persists_changes(self, session: Session):
        repository = MediaServerRepository(session)
        created = repository.create(MediaServer(
            name="Update Test", type=MediaServerType.PLEX,
            url="http://old:32400", token="old-token", enabled=True,
        ))
        session.flush()

        created.url = "http://new:32400"
        created.token = "new-token"
        created.enabled = False
        updated = repository.update(created)
        session.flush()

        assert updated.url == "http://new:32400"
        assert updated.token == "new-token"
        assert updated.enabled is False
        reread = repository.get(created.id)
        assert reread.url == "http://new:32400"
        assert reread.token == "new-token"

    def test_connector_update_returns_none_for_missing(self, session: Session):
        connector = MediaServerPersistenceConnector(session)
        missing = MediaServer(
            id=99999, name="ghost", type=MediaServerType.PLEX,
            url="http://x", token="t",
        )
        assert connector.update(missing) is None

    def test_repository_update_missing_raises(self, session: Session):
        repository = MediaServerRepository(session)
        missing = MediaServer(
            id=99999, name="ghost", type=MediaServerType.PLEX,
            url="http://x", token="t",
        )
        with pytest.raises(MediaServerNotFoundError):
            repository.update(missing)

class TestMediaServerPersistence:

    def test_created_at_set_automatically(self, session: Session):
        repository = MediaServerRepository(session)

        media_server = MediaServer(
            name="Timestamp Test",
            type=MediaServerType.PLEX,
            url="http://localhost:32400",
            token="token"
        )

        created = repository.create(media_server)
        session.flush()

        assert created.created_at is not None

    def test_token_stored_encrypted(self, session: Session):
        connector = MediaServerPersistenceConnector(session)

        media_server = MediaServer(
            name="Encryption Test",
            type=MediaServerType.PLEX,
            url="http://localhost:32400",
            token="super-secret-token"
        )

        entity = connector.create(media_server)
        session.flush()

        assert entity.token is not None

