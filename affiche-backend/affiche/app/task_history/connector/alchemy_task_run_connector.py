from typing import List

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from affiche.app.task_history.connector.task_run_entity import TaskRunEntity
from affiche.app.task_history.model.task_run import TaskRun, TaskRunSearch

_MUTABLE = ("status", "started_at", "ended_at", "items_done", "items_total",
            "message", "error", "resource", "media_server_id", "library_id", "blocking")

class AlchemyTaskRunConnector:

    def __init__(self, session: Session):
        self._session = session

    def save(self, run: TaskRun) -> TaskRun:
        entity = self._session.execute(
            select(TaskRunEntity).where(TaskRunEntity.task_id == run.task_id)
        ).scalar_one_or_none()

        if entity is None:
            entity = TaskRunEntity(task_id=run.task_id, task_name=run.task_name,
                                   created_at=run.created_at)
            self._session.add(entity)

        for field in _MUTABLE:
            value = getattr(run, field)
            if value is not None:
                setattr(entity, field, value)

        self._session.commit()
        self._session.refresh(entity)
        return TaskRun.model_validate(entity)

    def find_recent(self, search: TaskRunSearch) -> List[TaskRun]:
        query = select(TaskRunEntity).order_by(TaskRunEntity.created_at.desc(),
                                               TaskRunEntity.id.desc())
        if search.library_id is not None:
            query = query.where(TaskRunEntity.library_id == search.library_id)
        if search.page_size is not None:
            query = query.offset(search.offset).limit(search.page_size)

        entities = self._session.execute(query).scalars().all()
        return [TaskRun.model_validate(entity) for entity in entities]

    def count(self) -> int:
        return self._session.execute(select(func.count(TaskRunEntity.id))).scalar() or 0

    def prune(self, keep: int) -> int:
        keepers = self._session.execute(
            select(TaskRunEntity.id)
            .order_by(TaskRunEntity.created_at.desc(), TaskRunEntity.id.desc())
            .limit(keep)
        ).scalars().all()

        result = self._session.execute(
            delete(TaskRunEntity).where(TaskRunEntity.id.notin_(keepers))
        )
        self._session.commit()
        return result.rowcount or 0

    def delete_all(self) -> None:
        self._session.execute(delete(TaskRunEntity))
        self._session.commit()
