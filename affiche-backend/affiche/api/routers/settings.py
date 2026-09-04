import logging

from fastapi import APIRouter, Depends, HTTPException

from affiche import __version__

from affiche.api.schemas.settings_schema import (
    PosterConfigResponse,
    PosterConfigUpdate,
    OverlayOptionsResponse,
    TextOptionsResponse,
    GenerationOptionsResponse,
    AppSettingsResponse,
    AppSettingsUpdate,
    AppSettingsInfo,
)
from affiche.app.image.model import OverlayOptions, TextOptions, GenerationOptions
from affiche.config.app_settings_store import AppSettingsStore
from affiche.config.database import database_ok
from affiche.config.dependencies import (
    require_admin,
    get_poster_config_store,
    reset_poster_decorator,
    get_app_settings_store,
)
from affiche.config.env_config import is_using_legacy_encryption_key
from affiche.config.poster_config_store import PosterConfigStore

router = APIRouter()

logger = logging.getLogger(__name__)

APP_VERSION = __version__

def _poster_config_response(overlay: OverlayOptions, text: TextOptions,
                            generation: GenerationOptions) -> PosterConfigResponse:
    return PosterConfigResponse(
        overlay_options=OverlayOptionsResponse(**overlay.model_dump()),
        text_options=TextOptionsResponse(**text.model_dump()),
        generation_options=GenerationOptionsResponse(**generation.model_dump()),
    )

@router.get("/poster-config", response_model=PosterConfigResponse)
def get_poster_config(store: PosterConfigStore = Depends(get_poster_config_store)):
    overlay, text, generation = store.get()
    return _poster_config_response(overlay, text, generation)

@router.put("/poster-config", response_model=PosterConfigResponse, dependencies=[Depends(require_admin)])
def update_poster_config(update: PosterConfigUpdate,
                         store: PosterConfigStore = Depends(get_poster_config_store)):
    try:
        overlay = OverlayOptions(**update.overlay_options.model_dump())
        text = TextOptions(**update.text_options.model_dump())
        generation = GenerationOptions(**update.generation_options.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    store.save(overlay, text, generation)
    reset_poster_decorator()

    return _poster_config_response(overlay, text, generation)

@router.get("/", response_model=AppSettingsResponse)
def get_app_settings(store: AppSettingsStore = Depends(get_app_settings_store)):
    return AppSettingsResponse(**store.get().model_dump())

@router.put("/", response_model=AppSettingsResponse, dependencies=[Depends(require_admin)])
def update_app_settings(update: AppSettingsUpdate,
                        store: AppSettingsStore = Depends(get_app_settings_store)):
    try:
        settings = store.partial_update(update.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AppSettingsResponse(**settings.model_dump())

@router.get("/info", response_model=AppSettingsInfo)
def get_settings_info():
    return AppSettingsInfo(
        version=APP_VERSION,
        encryption_key_secure=not is_using_legacy_encryption_key(),
        database="connected" if database_ok() else "error",
    )
