from typing import List

from fastapi import APIRouter, Depends, Response

from affiche.api.schemas.style_profile import (
    StyleProfileCreate,
    StyleProfileResponse,
    StyleProfileUpdate,
)
from affiche.app.style_profile.model.style_profile import StyleProfile
from affiche.app.style_profile.service.style_profile_service import StyleProfileService
from affiche.config.dependencies import require_admin, get_style_profile_service

router = APIRouter()

def _response(profile: StyleProfile, library_count: int) -> StyleProfileResponse:
    return StyleProfileResponse(
        id=profile.id,
        name=profile.name,
        overlay_options=profile.overlay_options,
        text_options=profile.text_options,
        library_count=library_count,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )

@router.get("", response_model=List[StyleProfileResponse])
def list_style_profiles(
        service: StyleProfileService = Depends(get_style_profile_service)
) -> List[StyleProfileResponse]:
    return [_response(profile, service.count_libraries_using(profile.id))
            for profile in service.list_profiles()]

@router.post("", response_model=StyleProfileResponse, status_code=201,
             dependencies=[Depends(require_admin)])
def create_style_profile(
        request: StyleProfileCreate,
        service: StyleProfileService = Depends(get_style_profile_service)
) -> StyleProfileResponse:
    profile = service.create_profile(
        name=request.name,
        overlay_options=request.overlay_options,
        text_options=request.text_options,
    )
    return _response(profile, 0)

@router.patch("/{profile_id}", response_model=StyleProfileResponse, dependencies=[Depends(require_admin)])
def update_style_profile(
        profile_id: int,
        request: StyleProfileUpdate,
        service: StyleProfileService = Depends(get_style_profile_service)
) -> StyleProfileResponse:
    profile = service.update_profile(profile_id, request.model_dump(exclude_unset=True))
    return _response(profile, service.count_libraries_using(profile.id))

@router.delete("/{profile_id}", status_code=204, response_class=Response,
               dependencies=[Depends(require_admin)])
def delete_style_profile(
        profile_id: int,
        service: StyleProfileService = Depends(get_style_profile_service)
) -> Response:
    service.delete_profile(profile_id)
    return Response(status_code=204)
