from affiche.app.webhooks.webhook_parser import parse_jellyfin, parse_plex

def test_parse_plex_library_new():
    event = parse_plex({"event": "library.new",
                        "Metadata": {"librarySectionID": 7, "ratingKey": "123"}})
    assert event.is_new_item is True
    assert event.library_external_id == "7"

def test_parse_plex_ignores_other_events():
    event = parse_plex({"event": "media.play", "Metadata": {"librarySectionID": 7}})
    assert event.is_new_item is False

def test_parse_plex_missing_section():
    event = parse_plex({"event": "library.new"})
    assert event.is_new_item is True
    assert event.library_external_id is None

def test_parse_jellyfin_item_added():
    event = parse_jellyfin({"NotificationType": "ItemAdded", "ItemId": "abc", "LibraryId": "L1"})
    assert event.is_new_item is True
    assert event.library_external_id == "L1"

def test_parse_jellyfin_ignores_other_events():
    event = parse_jellyfin({"NotificationType": "PlaybackStart", "ItemId": "abc"})
    assert event.is_new_item is False

def test_parse_jellyfin_without_library():
    event = parse_jellyfin({"NotificationType": "ItemAdded", "ItemId": "abc"})
    assert event.is_new_item is True
    assert event.library_external_id is None
