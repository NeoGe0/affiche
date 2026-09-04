import pytest
from fastapi.testclient import TestClient

from affiche.app.image.font_store import (
    BundledFontError,
    FontNotFoundError,
    FontStore,
    FontTooLargeError,
    InvalidFontFileError,
    InvalidFontNameError,
    MAX_FONT_BYTES,
    RESOURCES_DIR,
)
from affiche.config.dependencies import get_font_store

def _a_real_font() -> bytes:
    for candidate in sorted(RESOURCES_DIR.glob("*.ttf")):
        return candidate.read_bytes()
    pytest.skip("no bundled .ttf to copy")

@pytest.fixture
def store(tmp_path):
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "Bundled-Regular.ttf").write_bytes(_a_real_font())
    return FontStore(bundled_dir=bundled, user_dir=tmp_path / "user")

@pytest.fixture
def client(authenticated_app, store):
    authenticated_app.dependency_overrides[get_font_store] = lambda: store
    yield TestClient(authenticated_app)
    authenticated_app.dependency_overrides.pop(get_font_store, None)

def test_listing_covers_both_directories_and_marks_only_uploads_deletable(store):
    store.save("Uploaded.ttf", _a_real_font())

    assert store.list_fonts() == ["Bundled-Regular.ttf", "Uploaded.ttf"]
    assert store.list_user_fonts() == ["Uploaded.ttf"]

def test_a_missing_user_directory_is_not_an_error(store):
    assert store.list_user_fonts() == []
    assert store.list_fonts() == ["Bundled-Regular.ttf"]

def test_non_font_files_are_ignored(store, tmp_path):
    (tmp_path / "bundled" / "notes.txt").write_text("not a font")

    assert store.list_fonts() == ["Bundled-Regular.ttf"]

@pytest.mark.parametrize("name", [
    "../../../etc/passwd.ttf",
    "sub/dir/Font.ttf",
    ".hidden.ttf",
    "",
])
def test_a_name_that_is_a_path_is_refused(store, name):
    with pytest.raises(InvalidFontNameError):
        store.safe_name(name)

@pytest.mark.parametrize("name", ["Font.exe", "Font", "Font.ttf.exe"])
def test_only_ttf_and_otf_are_accepted(store, name):
    with pytest.raises(InvalidFontNameError):
        store.safe_name(name)

def test_the_extension_check_is_case_insensitive(store):
    assert store.safe_name("Font.TTF") == "Font.TTF"

def test_reading_resolves_across_both_directories(store):
    store.save("Uploaded.ttf", _a_real_font())

    assert store.read("Bundled-Regular.ttf")
    assert store.read("Uploaded.ttf")

def test_reading_an_unlisted_name_is_not_found(store):
    with pytest.raises(FontNotFoundError):
        store.read("Nope.ttf")

def test_reading_cannot_be_aimed_outside_the_font_directories(store, tmp_path):
    secret = tmp_path / "secret.ttf"
    secret.write_bytes(b"sensitive")

    for name in ("../secret.ttf", str(secret)):
        with pytest.raises(FontNotFoundError):
            store.read(name)

def test_a_valid_upload_is_persisted_and_then_listed(store):
    assert store.save("New-Font.otf", _a_real_font()) == "New-Font.otf"
    assert "New-Font.otf" in store.list_user_fonts()

def test_a_file_pil_cannot_open_is_refused(store):
    with pytest.raises(InvalidFontFileError):
        store.save("Broken.ttf", b"this is not a font")

def test_an_empty_upload_is_refused(store):
    with pytest.raises(InvalidFontFileError):
        store.save("Empty.ttf", b"")

def test_an_oversized_upload_is_refused(store):
    with pytest.raises(FontTooLargeError):
        store.save("Huge.ttf", b"x" * (MAX_FONT_BYTES + 1))

def test_an_upload_cannot_escape_the_user_directory(store, tmp_path):
    with pytest.raises(InvalidFontNameError):
        store.save("../../escaped.ttf", _a_real_font())
    assert not (tmp_path / "escaped.ttf").exists()

def test_an_uploaded_font_can_be_deleted(store):
    store.save("Temp.ttf", _a_real_font())
    store.delete("Temp.ttf")

    assert store.list_user_fonts() == []

def test_a_bundled_font_cannot_be_deleted(store):
    with pytest.raises(BundledFontError):
        store.delete("Bundled-Regular.ttf")

    assert "Bundled-Regular.ttf" in store.list_fonts()

def test_deleting_an_unknown_font_is_not_found(store):
    with pytest.raises(FontNotFoundError):
        store.delete("Nope.ttf")

def test_the_endpoints_map_each_refusal_to_its_own_status(client, store):
    assert client.get("/affiche/service/fonts").json() == ["Bundled-Regular.ttf"]
    assert client.get("/affiche/service/user-fonts").json() == []

    assert client.get("/affiche/service/fonts/Bundled-Regular.ttf").status_code == 200
    assert client.get("/affiche/service/fonts/Nope.ttf").status_code == 404

    upload = client.post("/affiche/service/fonts",
                         files={"file": ("Uploaded.ttf", _a_real_font(), "font/ttf")})
    assert upload.status_code == 201
    assert upload.json() == {"name": "Uploaded.ttf"}
    assert client.get("/affiche/service/user-fonts").json() == ["Uploaded.ttf"]

    assert client.post("/affiche/service/fonts",
                       files={"file": ("Broken.ttf", b"nope", "font/ttf")}).status_code == 400
    assert client.post(
        "/affiche/service/fonts",
        files={"file": ("Huge.ttf", b"x" * (MAX_FONT_BYTES + 1), "font/ttf")},
    ).status_code == 413

    assert client.request("DELETE", "/affiche/service/fonts/Bundled-Regular.ttf").status_code == 400
    assert client.request("DELETE", "/affiche/service/fonts/Uploaded.ttf").status_code == 204
    assert client.request("DELETE", "/affiche/service/fonts/Uploaded.ttf").status_code == 404

def test_a_served_font_is_cacheable(client):
    response = client.get("/affiche/service/fonts/Bundled-Regular.ttf")

    assert response.headers["cache-control"] == "public, max-age=604800"
