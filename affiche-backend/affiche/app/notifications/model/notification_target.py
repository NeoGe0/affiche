from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

class NotificationType(str, Enum):
    DISCORD = "discord"
    GOTIFY = "gotify"
    APPRISE = "apprise"
    WEBHOOK = "webhook"

class NotificationEvent(str, Enum):
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    ITEMS_ERRORED = "items_errored"

class NotificationTarget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str = Field(min_length=1, max_length=100)
    type: NotificationType
    url: str = Field(min_length=1, max_length=1024)
    enabled: bool = True
    on_task_completed: bool = True
    on_task_failed: bool = True
    on_items_errored: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def wants(self, event: NotificationEvent) -> bool:
        if not self.enabled:
            return False
        return {
            NotificationEvent.TASK_COMPLETED: self.on_task_completed,
            NotificationEvent.TASK_FAILED: self.on_task_failed,
            NotificationEvent.ITEMS_ERRORED: self.on_items_errored,
        }[event]
