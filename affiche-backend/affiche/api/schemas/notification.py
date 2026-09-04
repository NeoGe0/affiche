from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from affiche.app.notifications.model.notification_target import NotificationType

class NotificationTargetResponse(BaseModel):
    id: int
    name: str
    type: NotificationType
    url_hint: str
    enabled: bool
    on_task_completed: bool
    on_task_failed: bool
    on_items_errored: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class NotificationTargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: NotificationType
    url: str = Field(min_length=1, max_length=1024)
    enabled: bool = True
    on_task_completed: bool = True
    on_task_failed: bool = True
    on_items_errored: bool = True

class NotificationTargetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    type: Optional[NotificationType] = None
    url: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    enabled: Optional[bool] = None
    on_task_completed: Optional[bool] = None
    on_task_failed: Optional[bool] = None
    on_items_errored: Optional[bool] = None

class NotificationTestRequest(BaseModel):
    type: NotificationType
    url: str
    name: str = "This target"

class NotificationTestResult(BaseModel):
    delivered: bool
