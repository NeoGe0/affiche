import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from affiche.app.asynch.auto_pickup import pickup_for_new_item
from affiche.app.mediaserver.model.media_server import MediaServerType
from affiche.app.webhooks.webhook_parser import parse_jellyfin, parse_plex
from affiche.config.database import get_db
from affiche.config.dependencies import container

router = APIRouter()

logger = logging.getLogger(__name__)

async def _read_payload(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        raw = form.get("payload")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    try:
        return await request.json()
    except Exception:
        return {}

@router.post("/{token}")
async def receive_webhook(token: str, request: Request, session: Session = Depends(get_db)):
    ms_service = container.media_server_service(session)
    server = ms_service.get_by_webhook_token(token)
    if server is None or not server.webhook_enabled:
        logger.warning("Webhook rejected: unknown or disabled token (…%s)", token[-6:])
        raise HTTPException(status_code=404, detail="Unknown webhook")

    payload = await _read_payload(request)
    event = (parse_plex(payload) if server.type == MediaServerType.PLEX
             else parse_jellyfin(payload))
    raw_event = payload.get("event") or payload.get("NotificationType") or "?"
    logger.info("Webhook received from '%s' (%s): event=%s new_item=%s library_ext_id=%s",
                server.name, server.type.value, raw_event, event.is_new_item,
                event.library_external_id)

    if not event.is_new_item:
        return {"status": "ignored"}

    dispatched = pickup_for_new_item(session, server, event.library_external_id, dispatch=True)
    return {"status": "accepted", "libraries": [lib["id"] for lib in dispatched]}

