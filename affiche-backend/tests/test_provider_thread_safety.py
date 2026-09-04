import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import affiche.external.plex.service.plex_service as plex_module
import affiche.external.poster.provider.tvdb as tvdb_module
from affiche.app.mediaserver.service.media_server_connector_factory import MediaServerConnectorFactory
from affiche.external.plex.service.plex_service import PlexService
from affiche.external.poster.provider.fanart import FanartClient
from affiche.external.poster.provider.mediux import MediuxClient
from affiche.external.poster.provider.tmdb import TMDBClient
from affiche.external.poster.provider.tvmaze import TVmazeClient

THREADS = 4

def _in_threads(fn, count: int = THREADS) -> list:
    barrier = threading.Barrier(count)

    def worker(_):
        barrier.wait()
        return fn()

    with ThreadPoolExecutor(max_workers=count) as executor:
        return list(executor.map(worker, range(count)))

def test_each_thread_gets_its_own_session():
    client = TMDBClient(api_key="k")

    sessions = _in_threads(lambda: client.session)

    assert len({id(s) for s in sessions}) == THREADS

def test_a_session_is_reused_within_one_thread():
    client = TMDBClient(api_key="k")

    assert client.session is client.session

def test_a_worker_threads_session_carries_the_auth_header():
    client = TMDBClient(api_key="secret")

    headers = _in_threads(lambda: dict(client.session.headers))

    assert all(h["Authorization"] == "Bearer secret" for h in headers)

def test_mediux_configures_each_threads_session_too():
    client = MediuxClient(api_key="Bearer abc123")

    headers = _in_threads(lambda: dict(client.session.headers))

    assert all(h["Authorization"] == "Bearer abc123" for h in headers)

def test_fanart_carries_its_api_key_param_per_thread():
    client = FanartClient(api_key="fk")

    params = _in_threads(lambda: dict(client.session.params))

    assert all(p == {"api_key": "fk"} for p in params)

def test_an_injected_session_applies_to_every_thread():
    client = TMDBClient(api_key="k")
    stub = MagicMock()
    client.session = stub

    assert all(s is stub for s in _in_threads(lambda: client.session))

def test_tvmaze_shares_its_throttle_and_cache_but_not_its_session():
    client = TVmazeClient()

    seen = _in_threads(lambda: (id(client._throttle_lock), id(client._show_id_cache),
                                id(client.session)))

    assert len({lock for lock, _, _ in seen}) == 1, "throttle lock must be shared"
    assert len({cache for _, cache, _ in seen}) == 1, "show-id cache must be shared"
    assert len({session for _, _, session in seen}) == THREADS, "session must not be"

def test_plex_client_is_built_exactly_once_under_concurrency():
    built = []

    def slow_constructor(*args, **kwargs):
        built.append(1)
        time.sleep(0.02)
        return MagicMock()

    with patch.object(plex_module, "PlexServer", side_effect=slow_constructor):
        service = PlexService("http://plex", "token")
        clients = _in_threads(lambda: service.plex)

    assert len(built) == 1, f"PlexServer constructed {len(built)}x — one handshake per race"
    assert all(c is clients[0] for c in clients)

def test_connector_is_built_exactly_once_under_concurrency():
    factory = MediaServerConnectorFactory(session_factory=MagicMock())
    built = []

    def slow_create(_media_server_id):
        built.append(1)
        time.sleep(0.02)
        return MagicMock()

    factory._create_connector = slow_create
    connectors = _in_threads(lambda: factory.get(1))

    assert len(built) == 1, f"connector built {len(built)}x — one handshake per race"
    assert all(c is connectors[0] for c in connectors)

def test_invalidating_a_connector_forces_a_rebuild():
    factory = MediaServerConnectorFactory(session_factory=MagicMock())
    factory._create_connector = lambda _id: MagicMock()

    first = factory.get(1)
    factory.invalidate(1)
    second = factory.get(1)

    assert first is not second

def test_tvdb_client_is_built_exactly_once_under_concurrency():
    built = []

    def slow_constructor(*args, **kwargs):
        built.append(1)
        time.sleep(0.02)
        return MagicMock()

    with patch.object(tvdb_module, "TVDB", side_effect=slow_constructor):
        client = tvdb_module.TVDBClient(api_key="k")
        clients = _in_threads(lambda: client.tvdb)

    assert len(built) == 1, f"TVDB constructed {len(built)}x — one login per race"
    assert all(c is clients[0] for c in clients)
