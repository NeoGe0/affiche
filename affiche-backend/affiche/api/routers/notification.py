from typing import List
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Response

from affiche.api.schemas.notification import (
    NotificationTargetCreate,
    NotificationTargetResponse,
    NotificationTargetUpdate,
    NotificationTestRequest,
    NotificationTestResult,
)
from affiche.app.notifications.model.notification_target import NotificationTarget
from affiche.app.notifications.service.notification_service import NotificationService
from affiche.config.dependencies import get_notification_service, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

def _url_hint(url: str) -> str:
    try:
        return urlparse(url).hostname or "(unknown host)"
    except ValueError:
        return "(unparseable URL)"

def _response(target: NotificationTarget) -> NotificationTargetResponse:
    return NotificationTargetResponse(
        id=target.id,
        name=target.name,
        type=target.type,
        url_hint=_url_hint(target.url),
        enabled=target.enabled,
        on_task_completed=target.on_task_completed,
        on_task_failed=target.on_task_failed,
        on_items_errored=target.on_items_errored,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )

@router.get("", response_model=List[NotificationTargetResponse])
def list_notification_targets(
        service: NotificationService = Depends(get_notification_service)
) -> List[NotificationTargetResponse]:
    return [_response(target) for target in service.list_targets()]

@router.post("", response_model=NotificationTargetResponse, status_code=201)
def create_notification_target(
        request: NotificationTargetCreate,
        service: NotificationService = Depends(get_notification_service)
) -> NotificationTargetResponse:
    return _response(service.create_target(NotificationTarget(**request.model_dump())))

@router.patch("/{target_id}", response_model=NotificationTargetResponse)
def update_notification_target(
        target_id: int,
        request: NotificationTargetUpdate,
        service: NotificationService = Depends(get_notification_service)
) -> NotificationTargetResponse:
    return _response(service.update_target(target_id, request.model_dump(exclude_unset=True)))

@router.delete("/{target_id}", status_code=204, response_class=Response)
def delete_notification_target(
        target_id: int,
        service: NotificationService = Depends(get_notification_service)
) -> Response:
    service.delete_target(target_id)
    return Response(status_code=204)

@router.post("/test", response_model=NotificationTestResult)
def test_notification_url(
        request: NotificationTestRequest,
        service: NotificationService = Depends(get_notification_service)
) -> NotificationTestResult:
    return NotificationTestResult(
        delivered=service.send_test_to(request.type, request.url, request.name))

@router.post("/{target_id}/test", response_model=NotificationTestResult)
def test_notification_target(
        target_id: int,
        service: NotificationService = Depends(get_notification_service)
) -> NotificationTestResult:
    return NotificationTestResult(delivered=service.send_test(target_id))
