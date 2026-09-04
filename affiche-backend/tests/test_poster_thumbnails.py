from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

import affiche.main  # noqa: F401  -- import first; `container` alone hits a circular import
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.image.thumbnail import THUMBNAIL_WIDTH, make_thumbnail
from affiche.config.dependencies import container

LIB_ID = 971
ITEM_ID = 972
SEASON = 4

ITEM_URL = f"/affiche/libraries/{LIB_ID}/items/{ITEM_ID}/poster"
SEASON_URL = f"/affiche/libraries/{LIB_ID}/items/{ITEM_ID}/seasons/{SEASON}/poster"

def poster_bytes(width: int = 1000, height: int = 1500, colour: str = "navy") -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (width, height), colour)
    for y in range(0, height, 7):
        for x in range(0, width, 11):
            image.putpixel((x, y), ((x * 7) % 256, (y * 3) % 256, (x + y) % 256))
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()

def test_thumbnail_is_downscaled_to_the_target_width():
    thumb = make_thumbnail(poster_bytes())

    with Image.open(BytesIO(thumb)) as image:
        assert image.width == THUMBNAIL_WIDTH
        assert image.height == THUMBNAIL_WIDTH * 3 // 2

def test_thumbnail_is_dramatically_smaller_than_the_poster():
    full = poster_bytes()
    thumb = make_thumbnail(full)

    assert len(thumb) * 5 < len(full), (
        f"thumbnail {len(thumb)}B vs poster {len(full)}B — not worth the round trip"
    )

def test_thumbnail_does_not_upscale_a_small_poster():
    thumb = make_thumbnail(poster_bytes(width=120, height=180))

    with Image.open(BytesIO(thumb)) as image:
        assert image.width == 120

def test_thumbnail_handles_a_poster_with_alpha():
    buffer = BytesIO()
    Image.new("RGBA", (600, 900), (10, 20, 30, 128)).save(buffer, format="PNG")

    with Image.open(BytesIO(make_thumbnail(buffer.getvalue()))) as image:
        assert image.mode == "RGB"

def test_save_writes_the_thumbnail_alongside_the_poster(tmp_path):
    store = FileStoreService(root_dir=tmp_path, thumbnailer=make_thumbnail)
    full = poster_bytes()
    store.save(1, 42, full)

    thumbs = [p for p in tmp_path.rglob("*_thumb.jpg")]
    assert len(thumbs) == 1
    assert 0 < thumbs[0].stat().st_size < len(full)

def test_thumbnail_is_derived_on_demand_for_a_poster_saved_without_one(tmp_path):
    legacy = FileStoreService(root_dir=tmp_path)
    legacy.save(1, 42, poster_bytes())
    assert not list(tmp_path.rglob("*_thumb.jpg"))

    store = FileStoreService(root_dir=tmp_path, thumbnailer=make_thumbnail)
    derived = store.fetch_thumbnail(1, 42)

    assert len(derived) < len(store.fetch(1, 42))
    assert list(tmp_path.rglob("*_thumb.jpg")), "the derived thumbnail should be stored, not rebuilt"

def test_a_stale_thumbnail_is_rebuilt(tmp_path):
    store = FileStoreService(root_dir=tmp_path, thumbnailer=make_thumbnail)
    store.save(1, 42, poster_bytes(colour="navy"))
    before = store.fetch_thumbnail(1, 42)

    FileStoreService(root_dir=tmp_path).save(1, 42, poster_bytes(colour="darkred"))

    assert store.fetch_thumbnail(1, 42) != before

def test_thumbnail_falls_back_to_the_poster_when_it_cannot_be_built(tmp_path):
    def explode(_: bytes) -> bytes:
        raise ValueError("nope")

    store = FileStoreService(root_dir=tmp_path, thumbnailer=explode)
    full = poster_bytes()
    store.save(1, 42, full)

    assert store.fetch_thumbnail(1, 42) == full
    assert not list(tmp_path.rglob("*_thumb.jpg")), "a failed thumbnail must not be left behind"

def test_missing_poster_still_raises_rather_than_inventing_a_thumbnail(tmp_path):
    store = FileStoreService(root_dir=tmp_path, thumbnailer=make_thumbnail)
    try:
        store.fetch_thumbnail(1, 42)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")

def test_deleting_a_poster_removes_its_thumbnail(tmp_path):
    store = FileStoreService(root_dir=tmp_path, thumbnailer=make_thumbnail)
    store.save(1, 42, poster_bytes())
    assert list(tmp_path.rglob("*_thumb.jpg"))

    store.delete(1, 42)

    assert not list(tmp_path.rglob("*_thumb.jpg"))

def test_seasons_get_their_own_thumbnail(tmp_path):
    store = FileStoreService(root_dir=tmp_path, thumbnailer=make_thumbnail)
    store.save(1, 42, poster_bytes(colour="navy"))
    store.save(1, 42, poster_bytes(colour="darkgreen"), season_number=2)

    assert store.fetch_thumbnail(1, 42, season_number=2) != store.fetch_thumbnail(1, 42)

def test_route_serves_the_thumbnail_and_caches_it_immutably(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, poster_bytes())
        version = container.file_store.version(LIB_ID, ITEM_ID)

        thumb = client.get(ITEM_URL, params={"v": version, "size": "thumb"})
        full = client.get(ITEM_URL, params={"v": version})

        assert thumb.status_code == 200
        assert thumb.headers["cache-control"] == "private, max-age=31536000, immutable"
        assert len(thumb.content) * 5 < len(full.content)

def test_route_defaults_to_the_full_poster(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, poster_bytes())

        assert client.get(ITEM_URL).content == container.file_store.fetch(LIB_ID, ITEM_ID)

def test_the_two_sizes_are_separate_cache_entries(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, poster_bytes())

        thumb_etag = client.get(ITEM_URL, params={"size": "thumb"}).headers["etag"]
        full_etag = client.get(ITEM_URL).headers["etag"]
        assert thumb_etag != full_etag

        assert client.get(ITEM_URL, headers={"If-None-Match": thumb_etag}).status_code == 200
        assert client.get(ITEM_URL, headers={"If-None-Match": full_etag}).status_code == 304

def test_thumb_revalidates_against_its_own_etag(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, poster_bytes())

        etag = client.get(ITEM_URL, params={"size": "thumb"}).headers["etag"]
        again = client.get(ITEM_URL, params={"size": "thumb"}, headers={"If-None-Match": etag})

        assert again.status_code == 304

def test_season_route_serves_thumbnails(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, poster_bytes(), season_number=SEASON)

        thumb = client.get(SEASON_URL, params={"size": "thumb"})
        full = client.get(SEASON_URL)

        assert thumb.status_code == 200
        assert len(thumb.content) * 5 < len(full.content)

def test_unknown_size_is_rejected(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, poster_bytes())

        assert client.get(ITEM_URL, params={"size": "huge"}).status_code == 400
