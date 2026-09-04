from io import BytesIO

import pytest
import requests
from fastapi.testclient import TestClient
from PIL import Image

import affiche.app.image.custom_poster as cp
from affiche.api.schemas.library import ApplyPosterRequest
from affiche.main import app

STAGE_URL = "/affiche/service/custom-poster"

def _png_bytes(color=(200, 30, 30)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (10, 15), color).save(buf, "PNG")
    return buf.getvalue()

@pytest.fixture(autouse=True)
def staging_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "CUSTOM_POSTER_DIR", str(tmp_path / "custom"))
    return tmp_path

@pytest.fixture
def client(authenticated_app):
    return TestClient(authenticated_app)

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

def test_stage_resolve_roundtrip():
    token = cp.stage_bytes(_png_bytes())
    assert len(token) == 32
    path = cp.staged_path(token)
    assert path is not None and path.is_file()
    assert cp.resolve_source(f"custom:{token}") == str(path)
    assert cp.media_type_of(path) == "image/png"

def test_resolve_passes_through_normal_urls():
    assert cp.resolve_source("https://image.tmdb.org/x.jpg") == "https://image.tmdb.org/x.jpg"

def test_bad_tokens_rejected():
    assert cp.staged_path("../../etc/passwd") is None
    assert cp.staged_path("not-hex") is None
    assert cp.staged_path("a" * 40) is None
    with pytest.raises(cp.CustomPosterError):
        cp.resolve_source("custom:deadbeefdeadbeefdeadbeefdeadbeef")

def test_non_image_rejected():
    with pytest.raises(cp.CustomPosterError):
        cp.stage_bytes(b"this is not an image")

@pytest.mark.parametrize("url", [
    "http://127.0.0.1/a.png", "http://localhost/a.png",
    "http://169.254.169.254/latest", "http://10.0.0.5/x.png", "ftp://host/x",
])
def test_download_blocks_ssrf(url):
    with pytest.raises(cp.CustomPosterError):
        cp.download_user_image(url)

def test_stage_file_then_serve(client):
    png = _png_bytes()
    resp = client.post(STAGE_URL, files={"file": ("poster.png", png, "image/png")})
    assert resp.status_code == 201, resp.text
    token = resp.json()["token"]

    served = client.get(f"{STAGE_URL}/{token}")
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/png")
    assert served.content == png

def test_serve_unknown_token_404(client):
    assert client.get(f"{STAGE_URL}/deadbeefdeadbeefdeadbeefdeadbeef").status_code == 404

def test_stage_requires_exactly_one_input(client):
    assert client.post(STAGE_URL).status_code == 400
    both = client.post(STAGE_URL, files={"file": ("p.png", _png_bytes(), "image/png")},
                       data={"url": "https://example.com/x.png"})
    assert both.status_code == 400

def test_stage_url_downloads_via_guarded_fetch(client, monkeypatch):
    monkeypatch.setattr(cp.socket, "getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])
    monkeypatch.setattr(cp.requests, "get",
                        lambda *a, **k: FakeResponse(headers={"content-type": "image/png"},
                                                     body=_png_bytes()))
    resp = client.post(STAGE_URL, data={"url": "https://example.com/poster.png"})
    assert resp.status_code == 201, resp.text
    assert client.get(f"{STAGE_URL}/{resp.json()['token']}").status_code == 200

def test_stage_url_private_ip_rejected(client, monkeypatch):
    monkeypatch.setattr(cp.socket, "getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 80))])
    resp = client.post(STAGE_URL, data={"url": "http://sneaky.example/x.png"})
    assert resp.status_code == 400

def _apply_request(poster_url: str) -> ApplyPosterRequest:
    return ApplyPosterRequest(poster_url=poster_url)

def test_apply_resolver_maps_and_passes_through():
    token = cp.stage_bytes(_png_bytes())
    assert _apply_request(f"custom:{token}").resolved_poster_source() == str(cp.staged_path(token))
    assert _apply_request("https://x/y.jpg").resolved_poster_source() == "https://x/y.jpg"

def test_apply_resolver_rejects_missing_custom():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _apply_request("custom:deadbeefdeadbeefdeadbeefdeadbeef").resolved_poster_source()
    assert exc.value.status_code == 400
