from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from affiche.app.asynch.async_task_service import AsyncTaskService
from affiche.config.dependencies import get_async_task_service

router = APIRouter()

class TaskProgress(BaseModel):
    current: int
    total: int
    message: Optional[str] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str
    task_name: Optional[str] = None
    blocking: Optional[bool] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    failed_at: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[TaskProgress] = None
    result: Optional[dict] = None

class CancelResponse(BaseModel):
    success: bool
    message: str

@router.post("/{task_id}/cancel", response_model=CancelResponse)
def cancel_task(
    task_id: str,
    task_service: AsyncTaskService = Depends(get_async_task_service)
):
    success = task_service.cancel_task(task_id)
    if success:
        return CancelResponse(success=True, message=f"Task {task_id} cancelled")
    return CancelResponse(success=False, message=f"Task {task_id} could not be cancelled")

@router.get("/blocking/current", response_model=Optional[TaskStatus])
def get_running_blocking_task(
    task_service: AsyncTaskService = Depends(get_async_task_service)
):
    task = task_service.get_running_blocking_task()
    if not task:
        return None
    return TaskStatus(**task)

@router.get("/{task_id}", response_model=TaskStatus)
def get_task_status(
    task_id: str,
    task_service: AsyncTaskService = Depends(get_async_task_service)
):
    task = task_service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return TaskStatus(task_id=task_id, **task)

@router.get("/", response_model=List[TaskStatus])
def get_all_tasks(
    status: Optional[str] = None,
    task_service: AsyncTaskService = Depends(get_async_task_service)
):
    tasks = task_service.get_all_tasks(status)
    return [TaskStatus(**t) for t in tasks]

@router.get("/latest/{task_name}", response_model=Optional[TaskStatus])
def get_latest_task(
    task_name: str,
    task_service: AsyncTaskService = Depends(get_async_task_service)
):
    task = task_service.get_latest_task(task_name)
    if not task:
        return None
    return TaskStatus(**task)
