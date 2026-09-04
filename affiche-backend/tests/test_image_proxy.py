import pytest
import requests
from fastapi.testclient import TestClient

import affiche.app.image.image_proxy as proxy_module
from affiche.main import app

PROXY_URL = "/affiche/service/image-proxy"

class FakeResponse:

    def __init__(self, *, status_code=200, headers=None, body=b"", is_redirect=False):
        self.status_code = status_code
        self.headers = headers or {}
        self.is_redirect = is_redirect
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def iter_content(self, chunk_size):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

@pytest.fixture
def client(authenticated_app):
    return TestClient(authenticated_app)

def _patch_get(monkeypatch, response=None):
    calls = {"count": 0, "url": None}

    def fake_get(url, **kwargs):
        calls["count"] += 1
        calls["url"] = url
        assert kwargs.get("allow_redirects") is False
        assert kwargs.get("stream") is True
        return response

    monkeypatch.setattr(proxy_module.requests, "get", fake_get)
    return calls

def test_allowed_host_returns_image_without_wildcard_cors(client, monkeypatch):
    body = b"\xff\xd8\xff\xe0jpegdata"
    calls = _patch_get(monkeypatch, FakeResponse(
        headers={"content-type": "image/jpeg"}, body=body,
    ))

    resp = client.get(PROXY_URL, params={"url": "https://image.tmdb.org/t/p/original/x.jpg"})

    assert resp.status_code == 200
    assert resp.content == body
    assert resp.headers["content-type"].startswith("image/jpeg")
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}
    assert calls["count"] == 1

def test_metadata_ip_is_blocked_without_fetching(client, monkeypatch):
    calls = _patch_get(monkeypatch, FakeResponse())

    resp = client.get(PROXY_URL, params={"url": "http://169.254.169.254/latest/meta-data/"})

    assert resp.status_code == 403
    assert calls["count"] == 0

def test_lookalike_host_is_blocked(client, monkeypatch):
    calls = _patch_get(monkeypatch, FakeResponse())

    resp = client.get(PROXY_URL, params={"url": "https://eviltmdb.org/x.jpg"})

    assert resp.status_code == 403
    assert calls["count"] == 0

def test_non_image_content_type_rejected(client, monkeypatch):
    _patch_get(monkeypatch, FakeResponse(
        headers={"content-type": "text/html"}, body=b"<html></html>",
    ))

    resp = client.get(PROXY_URL, params={"url": "https://assets.fanart.tv/whatever"})

    assert resp.status_code == 400

def test_svg_is_rejected(client, monkeypatch):
    _patch_get(monkeypatch, FakeResponse(
        headers={"content-type": "image/svg+xml"},
        body=b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    ))

    resp = client.get(PROXY_URL, params={"url": "https://assets.fanart.tv/evil.svg"})

    assert resp.status_code == 400

def test_unknown_image_subtype_fails_closed(client, monkeypatch):
    _patch_get(monkeypatch, FakeResponse(
        headers={"content-type": "image/some-future-format"}, body=b"data",
    ))

    resp = client.get(PROXY_URL, params={"url": "https://assets.fanart.tv/x"})

    assert resp.status_code == 400

def test_content_type_parameters_are_tolerated_and_dropped(client, monkeypatch):
    _patch_get(monkeypatch, FakeResponse(
        headers={"content-type": "IMAGE/JPEG; charset=binary"}, body=b"\xff\xd8\xff\xe0",
    ))

    resp = client.get(PROXY_URL, params={"url": "https://image.tmdb.org/t/p/original/x.jpg"})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"

def test_response_forbids_content_sniffing(client, monkeypatch):
    _patch_get(monkeypatch, FakeResponse(
        headers={"content-type": "image/png"}, body=b"\x89PNG",
    ))

    resp = client.get(PROXY_URL, params={"url": "https://image.tmdb.org/t/p/original/x.png"})

    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"

def test_oversized_stream_rejected(client, monkeypatch):
    oversized = b"x" * (proxy_module.MAX_IMAGE_BYTES + 1)
    _patch_get(monkeypatch, FakeResponse(
        headers={"content-type": "image/jpeg"}, body=oversized,
    ))

    resp = client.get(PROXY_URL, params={"url": "https://artworks.thetvdb.com/banners/x.jpg"})

    assert resp.status_code == 413

def test_content_length_over_cap_rejected(client, monkeypatch):
    _patch_get(monkeypatch, FakeResponse(
        headers={"content-type": "image/jpeg",
                 "content-length": str(proxy_module.MAX_IMAGE_BYTES + 1)},
        body=b"short",
    ))

    resp = client.get(PROXY_URL, params={"url": "https://image.tmdb.org/t/p/original/x.jpg"})

    assert resp.status_code == 413

def test_redirect_refused(client, monkeypatch):
    _patch_get(monkeypatch, FakeResponse(
        status_code=302, headers={"location": "http://169.254.169.254/"}, is_redirect=True,
    ))

    resp = client.get(PROXY_URL, params={"url": "https://image.tmdb.org/t/p/original/x.jpg"})

    assert resp.status_code == 502

def test_invalid_scheme_rejected(client, monkeypatch):
    calls = _patch_get(monkeypatch, FakeResponse())

    resp = client.get(PROXY_URL, params={"url": "file:///etc/passwd"})

    assert resp.status_code == 400
    assert calls["count"] == 0

SHOKO_URL = "http://192.168.1.50:8111"
SHOKO_IMAGE = f"{SHOKO_URL}/api/v3/Image/e2f1"

class _FakeConfig:
    def __init__(self, url=SHOKO_URL, token="a-key", enabled=True):
        self.url = url
        self.token = token
        self.enabled = enabled

def _with_shoko_config(config):
    from affiche.config.dependencies import get_service_configuration_service

    class _Configs:
        def get_config(self, key):
            return config if key == "shoko" else None

    app.dependency_overrides[get_service_configuration_service] = lambda: _Configs()
    return lambda: app.dependency_overrides.pop(get_service_configuration_service, None)

def _patch_get_capturing(monkeypatch, response):
    calls = {"count": 0, "headers": None}

    def fake_get(url, **kwargs):
        calls["count"] += 1
        calls["headers"] = kwargs.get("headers") or {}
        return response

    monkeypatch.setattr(proxy_module.requests, "get", fake_get)
    return calls

def test_the_configured_shoko_origin_is_allowed_and_gets_the_key(client, monkeypatch):
    undo = _with_shoko_config(_FakeConfig())
    try:
        calls = _patch_get_capturing(monkeypatch, FakeResponse(
            headers={"content-type": "image/jpeg"}, body=b"\xff\xd8\xff\xe0",
        ))

        resp = client.get(PROXY_URL, params={"url": SHOKO_IMAGE})

        assert resp.status_code == 200
        assert calls["headers"]["apikey"] == "a-key"
    finally:
        undo()

@pytest.mark.parametrize("url", [
    "http://192.168.1.50:9000/api/v3/Image/e2f1",
    "http://192.168.1.51:8111/api/v3/Image/e2f1",
    "https://192.168.1.50:8111/api/v3/Image/e2f1",
    "http://169.254.169.254/latest/meta-data/",
])
def test_a_neighbouring_origin_is_still_refused(client, monkeypatch, url):
    undo = _with_shoko_config(_FakeConfig())
    try:
        calls = _patch_get_capturing(monkeypatch, FakeResponse())

        resp = client.get(PROXY_URL, params={"url": url})

        assert resp.status_code == 403
        assert calls["count"] == 0
    finally:
        undo()

@pytest.mark.parametrize("config", [
    None,
    _FakeConfig(enabled=False),
    _FakeConfig(token=""),
    _FakeConfig(url=""),
])
def test_the_exception_closes_when_shoko_is_not_usable(client, monkeypatch, config):
    undo = _with_shoko_config(config)
    try:
        calls = _patch_get_capturing(monkeypatch, FakeResponse())

        resp = client.get(PROXY_URL, params={"url": SHOKO_IMAGE})

        assert resp.status_code == 403
        assert calls["count"] == 0
    finally:
        undo()

def test_a_shoko_origin_still_cannot_return_an_svg(client, monkeypatch):
    undo = _with_shoko_config(_FakeConfig())
    try:
        _patch_get_capturing(monkeypatch, FakeResponse(
            headers={"content-type": "image/svg+xml"},
            body=b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        ))

        assert client.get(PROXY_URL, params={"url": SHOKO_IMAGE}).status_code == 400
    finally:
        undo()

def test_a_public_cdn_never_receives_the_shoko_key(client, monkeypatch):
    undo = _with_shoko_config(_FakeConfig())
    try:
        calls = _patch_get_capturing(monkeypatch, FakeResponse(
            headers={"content-type": "image/jpeg"}, body=b"\xff\xd8\xff\xe0",
        ))

        resp = client.get(PROXY_URL, params={"url": "https://image.tmdb.org/t/p/original/x.jpg"})

        assert resp.status_code == 200
        assert "apikey" not in calls["headers"]
    finally:
        undo()
