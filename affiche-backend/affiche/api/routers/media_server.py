import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from affiche.api.schemas.media_server import (
    AddLibrariesRequest,
    MediaServerCreate,
    MediaServerResponse,
    MediaServerTestResult,
    MediaServerLibrary,
    MediaServerTokenUpdate,
    PlexServiceCredentials,
    JellyfinServiceCredentials,
    LanguageOrderUpdate,
    PosterFallbackUpdate,
    WebhookUpdate,
)
from affiche.app.asynch.auto_pickup import pickup_for_new_item
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.media_server_probe_service import MediaServerProbeService
from affiche.app.mediaserver.service.media_server_service import MediaServerService
from affiche.app.auth.model.user import User, UserRole
from affiche.config.database import get_db
from affiche.config.dependencies import (
    get_current_user,
    get_media_server_probe_service,
    get_media_server_service,
    require_admin,
)

router = APIRouter()

logger = logging.getLogger(__name__)

_admin = [Depends(require_admin)]

def _readable(media_server: MediaServer, user: User) -> MediaServerResponse:
    response = MediaServerResponse.model_validate(media_server, from_attributes=True)
    if user.role != UserRole.ADMIN:
        response.webhook_token = None
    return response

@router.get("/", response_model=List[MediaServerResponse])
def search(service: MediaServerService = Depends(get_media_server_service),
           user: User = Depends(get_current_user)):
    return [_readable(server, user) for server in service.search()]

@router.post("/", response_model=MediaServerResponse, dependencies=_admin)
def create(config: MediaServerCreate, service=Depends(get_media_server_service)):
    media_server = MediaServer.model_validate(config.model_dump(exclude={"libraries"}))
    return service.create(media_server, config.libraries)

@router.get("/{id}", response_model=MediaServerResponse)
def get(id: int, service: MediaServerService = Depends(get_media_server_service),
        user: User = Depends(get_current_user)):
    return _readable(service.get(id), user)

@router.delete("/{id}", status_code=204, dependencies=_admin)
def delete(id: int, service: MediaServerService = Depends(get_media_server_service)):
    service.delete(id)

@router.patch("/{id}/language-order", response_model=MediaServerResponse, dependencies=_admin)
def set_language_order(id: int, update: LanguageOrderUpdate,
                       service: MediaServerService = Depends(get_media_server_service)):
    return service.partial_update(id, {"language_order": update.language_order})

@router.patch("/{id}/poster-fallback", response_model=MediaServerResponse, dependencies=_admin)
def set_poster_fallback(id: int, update: PosterFallbackUpdate,
                        service: MediaServerService = Depends(get_media_server_service)):
    return service.partial_update(id, update.model_dump(exclude_none=True))

@router.patch("/{id}/token", response_model=MediaServerResponse, dependencies=_admin)
def update_token(id: int, update: MediaServerTokenUpdate,
                 service: MediaServerService = Depends(get_media_server_service),
                 probe: MediaServerProbeService = Depends(get_media_server_probe_service)):
    token = update.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    media_server = service.get(id)
    probe.verify_token(media_server, token)

    updated = service.update_token(id, token)
    logger.info("Updated the stored token for media server '%s'", updated.name)
    return updated

@router.patch("/{id}/webhook", response_model=MediaServerResponse, dependencies=_admin)
def set_webhook(id: int, update: WebhookUpdate,
                service: MediaServerService = Depends(get_media_server_service)):
    return service.set_webhook_enabled(id, update.enabled)

@router.post("/{id}/webhook/regenerate", response_model=MediaServerResponse, dependencies=_admin)
def regenerate_webhook(id: int, service: MediaServerService = Depends(get_media_server_service)):
    return service.regenerate_webhook_token(id)

@router.post("/{id}/webhook/test", dependencies=_admin)
def test_webhook(id: int, dry_run: bool = True,
                 service: MediaServerService = Depends(get_media_server_service),
                 session: Session = Depends(get_db)):
    server = service.get(id)

    logger.info("Webhook TEST triggered for server '%s' (dry_run=%s)", server.name, dry_run)
    results = pickup_for_new_item(session, server, None, dispatch=not dry_run)
    return {"status": "ok", "dry_run": dry_run, "libraries": results}

@router.get("/{id}/available-libraries", response_model=List[MediaServerLibrary], dependencies=_admin)
def get_available_libraries(id: int, service: MediaServerService = Depends(get_media_server_service)):
    return service.get_available_libraries(id)

@router.post("/{id}/available-libraries", status_code=201, dependencies=_admin)
def add_libraries(id: int, request: AddLibrariesRequest,
                  service: MediaServerService = Depends(get_media_server_service)):
    added = service.add_libraries(id, request.libraries,
                                  request.model_dump(exclude_unset=True, exclude={"libraries"}))
    return {"message": f"Added {added} libraries"}

@router.post("/plex/test", response_model=MediaServerTestResult, dependencies=_admin)
def plex_test_credentials(credentials: PlexServiceCredentials,
                          probe: MediaServerProbeService = Depends(get_media_server_probe_service)):
    return _test_result(probe.probe(MediaServerType.PLEX, credentials.url, credentials.token))

@router.post("/jellyfin/test", response_model=MediaServerTestResult, dependencies=_admin)
def jellyfin_test_credentials(credentials: JellyfinServiceCredentials,
                              probe: MediaServerProbeService = Depends(get_media_server_probe_service)):
    return _test_result(probe.probe(MediaServerType.JELLYFIN, credentials.url,
                                    credentials.api_key))

def _test_result(probed) -> MediaServerTestResult:
    return MediaServerTestResult(name=probed.name, libraries=probed.libraries)
