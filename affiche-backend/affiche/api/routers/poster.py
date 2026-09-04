import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from affiche.config.dependencies import (
    container,
)

router = APIRouter(tags=["Poster"])
logger = logging.getLogger(__name__)

IMMUTABLE_CACHE_CONTROL = "private, max-age=31536000, immutable"

REVALIDATE_CACHE_CONTROL = "private, max-age=60, must-revalidate"

def _poster_response(
        request: Request,
        requested_version: Optional[str],
        size: str,
        library_id: int,
        item_id: int,
        season_number: Optional[int] = None,
        variant: str = "generated",
        store=None,
) -> Response:
    if size not in ("full", "thumb"):
        raise HTTPException(status_code=400, detail="size must be 'full' or 'thumb'")
    if variant not in ("generated", "source"):
        raise HTTPException(status_code=400, detail="variant must be 'generated' or 'source'")
    if variant == "source" and size == "thumb":
        raise HTTPException(status_code=400, detail="the source poster has no thumbnail")

    store = store or container.file_store
    version = (store.source_version(library_id, item_id, season_number=season_number)
               if variant == "source"
               else store.version(library_id, item_id, season_number=season_number))
    if version is None:
        raise HTTPException(status_code=404, detail="Image not found")

    etag = f'"{version}-{size}-{variant}"'
    headers = {
        "ETag": etag,
        "Cache-Control": (
            IMMUTABLE_CACHE_CONTROL if requested_version == version else REVALIDATE_CACHE_CONTROL
        ),
    }

    if _matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)

    try:
        if variant == "source":
            content = store.fetch_source(library_id, item_id, season_number=season_number)
        elif size == "thumb":
            content = store.fetch_thumbnail(library_id, item_id, season_number=season_number)
        else:
            content = store.fetch(library_id, item_id, season_number=season_number)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(content=content, media_type="image/jpeg", headers=headers)

def _matches(if_none_match: Optional[str], etag: str) -> bool:
    if not if_none_match:
        return False
    if if_none_match.strip() == "*":
        return True
    for candidate in if_none_match.split(","):
        candidate = candidate.strip()
        if candidate.startswith("W/"):
            candidate = candidate[2:]
        if candidate == etag:
            return True
    return False

@router.get("/libraries/{library_id}/items/{item_id}/poster")
def get_item_poster(
        library_id: int,
        item_id: int,
        request: Request,
        v: Optional[str] = Query(None, description="Poster version, from the item's poster_version"),
        size: str = Query("full", description="'full' (source resolution) or 'thumb' (grid)"),
        variant: str = Query("generated", description="'generated' or 'source' (the server's own art)"),
) -> Response:
    return _poster_response(request, v, size, library_id, item_id, variant=variant)

@router.get("/libraries/{library_id}/collections/{collection_id}/poster")
def get_collection_poster(
        library_id: int,
        collection_id: int,
        request: Request,
        v: Optional[str] = Query(None, description="Poster version, from the collection's poster_version"),
        size: str = Query("full", description="'full' (source resolution) or 'thumb' (grid)"),
        variant: str = Query("generated", description="'generated' or 'source' (the server's own art)"),
) -> Response:
    return _poster_response(request, v, size, library_id, collection_id, variant=variant,
                            store=container.collection_file_store)

@router.get("/libraries/{library_id}/items/{item_id}/seasons/{season_number}/poster")
def get_season_poster(
        library_id: int,
        item_id: int,
        season_number: int,
        request: Request,
        v: Optional[str] = Query(None, description="Poster version, from the season's poster_version"),
        size: str = Query("full", description="'full' (source resolution) or 'thumb' (grid)"),
        variant: str = Query("generated", description="'generated' or 'source' (the server's own art)"),
) -> Response:
    return _poster_response(request, v, size, library_id, item_id, season_number=season_number,
                            variant=variant)
