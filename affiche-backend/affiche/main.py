import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from affiche import __version__

from affiche.app.events import event_manager

from affiche.api.routers.auth import router as auth_router
from affiche.api.routers.webhooks import router as webhooks_router
from affiche.api.routers.collection import router as collection_router
from affiche.api.routers.config import router
from affiche.api.routers.dashboard import router as dashboard_router
from affiche.api.routers.events import router as events_router
from affiche.api.routers.library import router as library_router
from affiche.api.routers.media_server import router as media_server_router
from affiche.api.routers.poster import router as poster_router
from affiche.api.routers.search import router as search_router
from affiche.api.routers.service import router as service_router
from affiche.api.routers.settings import router as settings_router
from affiche.api.routers.style_profile import router as style_profile_router
from affiche.api.routers.notification import router as notification_router
from affiche.api.routers.tasks import router as tasks_router
from affiche.config.database import database_ok, init_db
from affiche.config.dependencies import get_current_user, require_admin
from affiche.config.env_config import warn_if_legacy_encryption_key
from affiche.config.secrets_migration import reencrypt_legacy_secrets
from affiche.config.logging_config import setup_logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    setup_logging()
    warn_if_legacy_encryption_key()
    reencrypt_legacy_secrets()
    event_manager.set_loop(asyncio.get_running_loop())
    from affiche.app.asynch.auto_sync_scheduler import auto_sync_scheduler
    auto_sync_scheduler.start()
    from affiche.app.notifications.service.notifier import notifier
    notifier.start()
    logger.info("Application startup complete")
    yield
    auto_sync_scheduler.stop()
    notifier.stop()

app = FastAPI(
    title="Affiche",
    description="Automated poster replacement service for Plex and Jellyfin",
    version=__version__,
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

DEV_CORS_ORIGIN = "http://localhost:3000"

def cors_origins(is_packaged: bool, configured: Optional[str]) -> List[str]:
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [] if is_packaged else [DEV_CORS_ORIGIN]

_allowed_origins = cors_origins(STATIC_DIR.is_dir(), os.getenv("CORS_ORIGINS"))
if _allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS enabled for: %s", ", ".join(_allowed_origins))

@app.get("/health")
def health(response: Response):
    connected = database_ok()
    if not connected:
        response.status_code = 503
    return {
        "status": "healthy" if connected else "degraded",
        "database": "connected" if connected else "error",
    }

app.include_router(auth_router, prefix="/affiche/auth", tags=["auth"])
app.include_router(webhooks_router, prefix="/affiche/webhooks", tags=["webhooks"])

_protected = [Depends(get_current_user)]
_admin_only = [Depends(require_admin)]
app.include_router(router, prefix="/affiche/config", tags=["config"], dependencies=_admin_only)
app.include_router(media_server_router, prefix="/affiche/media-servers", tags=["media-server"], dependencies=_protected)
app.include_router(service_router, prefix="/affiche/service", tags=["service"], dependencies=_protected)
app.include_router(library_router, prefix="/affiche/media-servers", tags=["library"], dependencies=_protected)
app.include_router(collection_router, prefix="/affiche/media-servers", tags=["collection"], dependencies=_protected)
app.include_router(settings_router, prefix="/affiche/settings", tags=["settings"], dependencies=_protected)
app.include_router(style_profile_router, prefix="/affiche/style-profiles", tags=["style-profile"], dependencies=_protected)
app.include_router(notification_router, prefix="/affiche/notifications", tags=["notification"], dependencies=_protected)
app.include_router(tasks_router, prefix="/affiche/tasks", tags=["tasks"], dependencies=_protected)
app.include_router(events_router, prefix="/affiche/events", tags=["events"], dependencies=_protected)
app.include_router(dashboard_router, prefix="/affiche/dashboard", tags=["dashboard"], dependencies=_protected)
app.include_router(search_router, prefix="/affiche/search", tags=["search"], dependencies=_protected)
app.include_router(poster_router, prefix="/affiche", tags=["poster"], dependencies=_protected)

import affiche.api.exception_handler  # noqa: E402,F401

class _SpaStaticFiles(StaticFiles):

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            is_api = Path(path).parts[:1] == ("affiche",)
            if exc.status_code == 404 and not is_api:
                return await super().get_response("index.html", scope)
            raise

if STATIC_DIR.is_dir():
    app.mount("/", _SpaStaticFiles(directory=STATIC_DIR, html=True), name="spa")
else:
    @app.get("/")
    async def root():
        return {"status": "ok", "service": "Affiche"}
