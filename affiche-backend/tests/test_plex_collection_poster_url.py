from unittest.mock import MagicMock

from affiche.external.plex.service.plex_service import PlexService

COLLECTION_ART = "http://plex:32400/photo/:/transcode?url=%2Flibrary%2Fcollections%2F7%2Fcomposite"
COLLECTION_KEY = "/library/metadata/7"

def _collection(**overrides):
    collection = MagicMock()
    collection.ratingKey = 7
    collection.title = "Alien Saga"
    collection.key = COLLECTION_KEY
    collection.posterUrl = COLLECTION_ART
    collection.titleSort = None
    collection.childCount = 2
    for field, value in overrides.items():
        setattr(collection, field, value)
    return collection

def _service(collections):
    svc = object.__new__(PlexService)
    svc._plex = MagicMock()
    section = MagicMock()
    section.collections.return_value = collections
    svc._plex.library.sectionByID.return_value = section
    svc._plex.url.side_effect = \
        lambda key, includeToken=None: f"http://plex:32400{key}?X-Plex-Token=tok"
    svc._collection_members = MagicMock(return_value=[])
    return svc

def test_a_collection_carries_its_artwork_url():
    svc = _service([_collection()])

    assert svc.get_collections("1")[0].poster_url == COLLECTION_ART

def test_the_metadata_key_is_never_stored_as_the_poster():
    svc = _service([_collection()])

    poster_url = svc.get_collections("1")[0].poster_url

    assert COLLECTION_KEY not in poster_url

def test_a_collection_with_no_artwork_carries_no_url():
    svc = _service([_collection(posterUrl=None)])

    assert svc.get_collections("1")[0].poster_url is None
