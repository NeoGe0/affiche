import logging
from typing import Any, Dict, Optional

import requests

from affiche.app.notifications.model.notification_target import (
    NotificationEvent, NotificationType,
)
from affiche.config.http_config import HTTP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

GOTIFY_PRIORITY = 5

def build_payload(notification_type: NotificationType,
                  title: str,
                  message: str,
                  event: NotificationEvent,
                  details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if notification_type is NotificationType.DISCORD:
        return {"content": f"**{title}**\n{message}"}
    if notification_type is NotificationType.GOTIFY:
        return {"title": title, "message": message, "priority": GOTIFY_PRIORITY}
    if notification_type is NotificationType.APPRISE:
        return {"title": title, "body": message}
    return {"event": event.value, "title": title, "message": message, **(details or {})}

def send(notification_type: NotificationType,
         url: str,
         title: str,
         message: str,
         event: NotificationEvent,
         details: Optional[Dict[str, Any]] = None) -> bool:
    payload = build_payload(notification_type, title, message, event, details)
    try:
        response = requests.post(url, json=payload, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.warning("Notification to a %s target failed: %s", notification_type.value, e)
        return False
