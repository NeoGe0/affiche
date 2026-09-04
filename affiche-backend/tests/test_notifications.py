from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.api.routers.notification import _url_hint
from affiche.app.notifications.model.notification_target import (
    NotificationEvent, NotificationTarget, NotificationType,
)
from affiche.app.notifications.service.notification_service import NotificationService
from affiche.app.notifications.service.notifier import Notifier
from affiche.config.dependencies import get_notification_service
from affiche.external.notifications import notification_client

TARGET_URL = "https://discord.com/api/webhooks/1/secret"

def _target(**overrides) -> NotificationTarget:
    return NotificationTarget(**{
        "id": 1, "name": "Home", "type": NotificationType.DISCORD,
        "url": TARGET_URL, "enabled": True,
        "on_task_completed": True, "on_task_failed": True, "on_items_errored": True,
        **overrides,
    })

@pytest.mark.parametrize("event", list(NotificationEvent))
def test_a_disabled_target_hears_nothing(event):
    assert _target(enabled=False).wants(event) is False

@pytest.mark.parametrize("event,flag", [
    (NotificationEvent.TASK_COMPLETED, "on_task_completed"),
    (NotificationEvent.TASK_FAILED, "on_task_failed"),
    (NotificationEvent.ITEMS_ERRORED, "on_items_errored"),
])
def test_each_event_is_gated_by_its_own_flag(event, flag):
    assert _target(**{flag: False}).wants(event) is False
    assert _target(**{flag: True}).wants(event) is True

def test_notify_only_reaches_the_subscribed_targets():
    service = NotificationService(MagicMock())
    service._repository = MagicMock()
    service._repository.list_enabled.return_value = [
        _target(id=1, name="wants it"),
        _target(id=2, name="not this one", on_task_failed=False),
    ]

    with patch.object(notification_client, "send", return_value=True) as send:
        sent = service.notify(NotificationEvent.TASK_FAILED, "t", "m")

    assert sent == 1
    assert len(send.call_args_list) == 1

def test_one_dead_endpoint_does_not_cost_the_others_their_message():
    service = NotificationService(MagicMock())
    service._repository = MagicMock()
    service._repository.list_enabled.return_value = [_target(id=1), _target(id=2)]

    with patch.object(notification_client, "send", side_effect=[False, True]):
        assert service.notify(NotificationEvent.TASK_COMPLETED, "t", "m") == 1

def test_discord_gets_content_gotify_a_message_apprise_a_body():
    args = ("Title", "Body", NotificationEvent.TASK_COMPLETED)

    assert notification_client.build_payload(NotificationType.DISCORD, *args) == {
        "content": "**Title**\nBody"}
    assert notification_client.build_payload(NotificationType.GOTIFY, *args) == {
        "title": "Title", "message": "Body",
        "priority": notification_client.GOTIFY_PRIORITY}
    assert notification_client.build_payload(NotificationType.APPRISE, *args) == {
        "title": "Title", "body": "Body"}

def test_a_plain_webhook_gets_the_fields_rather_than_a_sentence():
    payload = notification_client.build_payload(
        NotificationType.WEBHOOK, "Title", "Body", NotificationEvent.TASK_FAILED,
        {"task_id": "abc"})

    assert payload == {"event": "task_failed", "title": "Title", "message": "Body",
                       "task_id": "abc"}

def test_a_failed_post_is_reported_not_raised():
    with patch.object(notification_client.requests, "post",
                      side_effect=requests.RequestException("no route")):
        assert notification_client.send(
            NotificationType.DISCORD, "https://x/y", "t", "m",
            NotificationEvent.TASK_COMPLETED) is False

def test_a_failed_run_reports_the_error():
    event, title, message = Notifier._compose("poster_sync_3", "failed", "boom", MagicMock())

    assert event is NotificationEvent.TASK_FAILED
    assert "poster_sync_3" in title
    assert message == "boom"

def test_a_failed_run_without_a_message_still_says_something():
    _, _, message = Notifier._compose("t", "failed", None, MagicMock())

    assert message

def test_a_clean_run_reports_completion():
    with patch.object(Notifier, "_errored_items", return_value=0):
        event, _, _ = Notifier._compose("library_sync_1_2", "completed", None, MagicMock())

    assert event is NotificationEvent.TASK_COMPLETED

def test_a_run_that_left_errors_reports_those_instead_of_a_plain_completion():
    with patch.object(Notifier, "_errored_items", return_value=4):
        event, _, message = Notifier._compose("poster_sync_3", "completed", None, MagicMock())

    assert event is NotificationEvent.ITEMS_ERRORED
    assert "4" in message

def test_an_uncountable_error_bucket_still_sends_the_completion():
    session = MagicMock()
    session.query.side_effect = RuntimeError("db gone")

    assert Notifier._errored_items(session) == 0

def test_the_error_count_covers_every_library(authenticated_app):
    from affiche.config.database import SessionLocal
    from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
    from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
    from affiche.app.mediaserver.library.service.library_service import LibraryService
    from affiche.app.mediaserver.library.model import Library, LibrarySearch
    from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity

    with TestClient(authenticated_app):
        session = SessionLocal()
    try:
        before = Notifier._errored_items(session)

        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name="Notif", type=MediaServerType.PLEX, url="http://x", token="t",
        ))
        session.flush()
        LibraryService(session).create(Library(
            media_server_id=server.id, external_id="sec-n", name="Films",
            type="movie", language="en", enabled=True,
        ))
        session.commit()
        library = LibraryService(session).find_libraries(
            LibrarySearch(media_server_id=server.id))[0]
        session.add_all([
            LibraryItemEntity(external_id="ok", library_id=library.id, title="Fine",
                              type="movie", processed=True),
            LibraryItemEntity(external_id="bad", library_id=library.id, title="Broken",
                              type="movie", processed=False, error_message="No poster found"),
        ])
        session.commit()

        assert Notifier._errored_items(session) == before + 1
    finally:
        session.close()

def test_delivery_failure_never_escapes_the_notifier():
    notifier = Notifier()
    with patch("affiche.app.notifications.service.notifier.SessionLocal",
               side_effect=RuntimeError("db gone")):
        notifier._deliver("id", "task", "completed", None)

def test_the_notifier_hands_the_work_off_the_task_thread():
    notifier = Notifier()
    notifier._executor = MagicMock()

    notifier._on_task_finished("id", "task", "completed", None)

    notifier._executor.submit.assert_called_once()

@pytest.fixture
def service(authenticated_app):
    stub = MagicMock()
    authenticated_app.dependency_overrides[get_notification_service] = lambda: stub
    yield stub
    authenticated_app.dependency_overrides.pop(get_notification_service, None)

def test_the_listing_never_returns_the_url(authenticated_app, service):
    service.list_targets.return_value = [_target()]

    with TestClient(authenticated_app) as client:
        body = client.get("/affiche/notifications").json()

    assert body[0]["url_hint"] == "discord.com"
    assert "secret" not in str(body)
    assert "url" not in body[0]

def test_a_patch_that_omits_the_url_keeps_the_stored_one(authenticated_app, service):
    service.update_target.return_value = _target(name="Renamed")

    with TestClient(authenticated_app) as client:
        client.patch("/affiche/notifications/1", json={"name": "Renamed"})

    assert service.update_target.call_args.args[1] == {"name": "Renamed"}

def test_a_url_can_be_tried_before_it_is_stored(authenticated_app, service):
    service.send_test_to.return_value = True

    with TestClient(authenticated_app) as client:
        body = client.post("/affiche/notifications/test", json={
            "type": "discord", "url": "https://discord.com/api/webhooks/x", "name": "Home",
        }).json()

    assert body == {"delivered": True}
    assert service.send_test_to.call_args.args == (
        NotificationType.DISCORD, "https://discord.com/api/webhooks/x", "Home")
    service.create_target.assert_not_called()
    service.update_target.assert_not_called()

def test_an_endpoint_that_refuses_the_test_is_an_answer_not_an_error(authenticated_app, service):
    service.send_test_to.return_value = False

    with TestClient(authenticated_app) as client:
        response = client.post("/affiche/notifications/test", json={
            "type": "gotify", "url": "https://gotify.example/message?token=nope",
        })

    assert response.status_code == 200
    assert response.json() == {"delivered": False}

def test_the_literal_test_path_is_not_read_as_a_target_id(authenticated_app, service):
    service.send_test_to.return_value = True

    with TestClient(authenticated_app) as client:
        response = client.post("/affiche/notifications/test", json={
            "type": "discord", "url": "https://discord.com/api/webhooks/x",
        })

    assert response.status_code == 200
    service.send_test.assert_not_called()

def test_an_unparseable_url_is_not_echoed_back_as_the_hint():
    assert _url_hint("not a url") == "(unknown host)"

@pytest.mark.parametrize("body,expected_status", [
    (lambda cancel_check=None: "fine", "completed"),
    (lambda cancel_check=None: (_ for _ in ()).throw(RuntimeError("boom")), "failed"),
])
def test_a_finished_task_publishes_to_the_internal_bus(body, expected_status):
    from affiche.app.asynch.async_task_service import AsyncTaskService
    from affiche.app.events import internal_event_bus

    seen = []
    handler = lambda **kwargs: seen.append(kwargs)
    internal_event_bus.subscribe("task.finished", handler)
    try:
        service = AsyncTaskService()
        service.submit_detached_task(body, task_name="job")
        service._executor.shutdown(wait=True)
    finally:
        internal_event_bus.unsubscribe("task.finished", handler)

    assert [(e["task_name"], e["status"]) for e in seen] == [("job", expected_status)]

def test_a_cancelled_task_stays_silent():
    from affiche.app.asynch.async_task_service import AsyncTaskService
    from affiche.app.events import internal_event_bus

    seen = []
    handler = lambda **kwargs: seen.append(kwargs)
    service = AsyncTaskService()
    task_id, _ = service.submit_detached_task(lambda cancel_check=None: None, task_name="job")
    service._executor.shutdown(wait=True)
    seen.clear()

    internal_event_bus.subscribe("task.finished", handler)
    try:
        service.cancel_task(task_id)
    finally:
        internal_event_bus.unsubscribe("task.finished", handler)

    assert seen == []
