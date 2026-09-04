import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.responses import Response

from affiche.api.schemas.service_schemas import PosterCandidate, ProviderTestRequest
from affiche.app.image import custom_poster
from affiche.app.image.font_store import (
    BundledFontError,
    FontNotFoundError,
    FontStore,
    FontTooLargeError,
    InvalidFontFileError,
    InvalidFontNameError,
    MAX_FONT_BYTES,
)
from affiche.app.image.image_proxy import (
    ImageFetchError,
    ImageHostNotAllowedError,
    ImageProxyService,
    ImageTooLargeError,
    InvalidImageUrlError,
    UnsupportedImageTypeError,
)
from affiche.app.service_configuration.exceptions import UnknownProviderError, ProviderConnectionError
from affiche.app.service_configuration.provider_service import ProviderService
from affiche.config.dependencies import (
    require_admin,
    get_font_store,
    get_image_proxy_service,
    get_poster_aggregator,
    get_provider_service,
)
from affiche.external.poster.poster_service import PosterAggregatorService

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/posters")
def get_posters(
        tmdb_id: Optional[int] = Query(None),
        tvdb_id: Optional[int] = Query(None),
        media_type: str = Query("movie"),
        provider: Optional[str] = Query(None),
        language: Optional[str] = Query(None),
        aggregator: PosterAggregatorService = Depends(get_poster_aggregator)
) -> List[PosterCandidate]:
    if media_type not in ("movie", "show"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'show'")
    if not tmdb_id and not tvdb_id:
        raise HTTPException(status_code=400, detail="At least one of tmdb_id or tvdb_id required")

    return aggregator.get_all_posters(
        media_type=media_type,
        tmdb_id=tmdb_id,
        tvdb_id=tvdb_id,
        language=language or None,
        provider_name=provider
    )

@router.get("/collection-posters")
def get_collection_posters(
        collection_id: int = Query(..., description="TMDB collection id"),
        provider: Optional[str] = Query(None),
        language: Optional[str] = Query(None),
        aggregator: PosterAggregatorService = Depends(get_poster_aggregator)
) -> List[PosterCandidate]:
    return aggregator.get_all_collection_posters(
        collection_id=collection_id,
        language=language or None,
        provider_name=provider,
    )

@router.get("/title")
def get_translated_title(
        media_type: str = Query("movie", description="Type: 'movie' or 'show'"),
        language: str = Query(..., description="ISO language code, e.g. 'fr'"),
        tmdb_id: Optional[int] = Query(None),
        tvdb_id: Optional[int] = Query(None),
        season_number: Optional[int] = Query(None),
        aggregator: PosterAggregatorService = Depends(get_poster_aggregator)
) -> dict:
    if media_type not in ("movie", "show"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'show'")
    if not tmdb_id and not tvdb_id:
        raise HTTPException(status_code=400, detail="At least one of tmdb_id or tvdb_id required")

    title = aggregator.get_translated_title(
        media_type=media_type,
        language=language,
        tmdb_id=tmdb_id,
        tvdb_id=tvdb_id,
        season_number=season_number,
    )
    return {"title": title}

@router.get("/image-proxy")
def proxy_image(
        url: str = Query(..., description="Image URL to proxy"),
        service: ImageProxyService = Depends(get_image_proxy_service),
):
    try:
        image = service.fetch(url)
    except (InvalidImageUrlError, UnsupportedImageTypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImageHostNotAllowedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ImageTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except ImageFetchError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return Response(
        content=image.content,
        media_type=image.content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Content-Type-Options": "nosniff",
        },
    )

@router.get("/posters/search")
def search_posters(
        name: str = Query(..., description="Movie or TV show title"),
        year: Optional[int] = Query(None, description="Release year (optional)"),
        media_type: str = Query("movie", description="Type: 'movie' or 'show'"),
        provider: Optional[str] = Query(None, description="Provider: 'tmdb', 'tvdb', or 'fanart'"),
        language: Optional[str] = Query(None),
        aggregator: PosterAggregatorService = Depends(get_poster_aggregator)
) -> List[PosterCandidate]:
    if media_type not in ("movie", "show"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'show'")

    ids = aggregator.search_by_title(name, media_type, year)

    if not ids.tmdb_id and not ids.tvdb_id:
        raise HTTPException(status_code=404, detail=f"Could not find '{name}' on any provider")

    return aggregator.get_all_posters(
        media_type=media_type,
        tmdb_id=ids.tmdb_id,
        tvdb_id=ids.tvdb_id,
        language=language or None,
        provider_name=provider
    )

@router.get("/posters/season")
def get_season_posters(
        season_number: int = Query(..., description="Season number"),
        tmdb_id: Optional[int] = Query(None),
        tvdb_id: Optional[int] = Query(None),
        provider: Optional[str] = Query(None),
        language: Optional[str] = Query(None),
        aggregator: PosterAggregatorService = Depends(get_poster_aggregator)
) -> List[PosterCandidate]:
    if not tmdb_id and not tvdb_id:
        raise HTTPException(status_code=400, detail="At least one of tmdb_id or tvdb_id required")

    return aggregator.get_all_season_posters(
        season_number=season_number,
        tmdb_id=tmdb_id,
        tvdb_id=tvdb_id,
        language=language or None,
        provider_name=provider
    )

@router.get("/fonts")
def list_fonts(store: FontStore = Depends(get_font_store)) -> List[str]:
    return store.list_fonts()

@router.get("/fonts/{filename}")
def get_font(filename: str, store: FontStore = Depends(get_font_store)) -> Response:
    try:
        content = store.read(filename)
    except FontNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=content,
        media_type="font/ttf",
        headers={"Cache-Control": "public, max-age=604800"},
    )

@router.get("/user-fonts")
def list_user_fonts(store: FontStore = Depends(get_font_store)) -> List[str]:
    return store.list_user_fonts()

@router.post("/fonts", status_code=201, dependencies=[Depends(require_admin)])
def upload_font(file: UploadFile = File(...),
                store: FontStore = Depends(get_font_store)) -> dict:
    content = file.file.read(MAX_FONT_BYTES + 1)
    try:
        return {"name": store.save(file.filename or "", content)}
    except FontTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except (InvalidFontNameError, InvalidFontFileError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/fonts/{filename}", status_code=204, dependencies=[Depends(require_admin)])
def delete_font(filename: str, store: FontStore = Depends(get_font_store)) -> Response:
    try:
        store.delete(filename)
    except FontNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (InvalidFontNameError, BundledFontError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(status_code=204)

@router.post("/custom-poster", status_code=201)
def stage_custom_poster(
        file: Optional[UploadFile] = File(None),
        url: Optional[str] = Form(None),
) -> dict:
    has_url = bool(url and url.strip())
    if bool(file) == has_url:
        raise HTTPException(status_code=400, detail="Provide exactly one of 'file' or 'url'")

    try:
        if has_url:
            data = custom_poster.download_user_image(url.strip())
        else:
            data = file.file.read(custom_poster.MAX_CUSTOM_POSTER_BYTES + 1)
        token = custom_poster.stage_bytes(data)
    except custom_poster.CustomPosterError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"token": token}

@router.get("/custom-poster/{token}")
def get_custom_poster(token: str):
    path = custom_poster.staged_path(token)
    if path is None:
        raise HTTPException(status_code=404, detail="Custom poster not found or expired")
    return Response(
        content=path.read_bytes(),
        media_type=custom_poster.media_type_of(path),
        headers={"Cache-Control": "private, max-age=3600"},
    )

@router.post("/provider/{provider}/test", dependencies=[Depends(require_admin)])
def provider_connection_test(provider: str,
                                   request: ProviderTestRequest,
                                   service: ProviderService = Depends(get_provider_service)):
    try:
        return service.test_provider_api_token(provider, request.api_key, request.url)
    except UnknownProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
