from typing import List

from sqlalchemy.orm import Session

from affiche.app.task_history.connector.alchemy_task_run_connector import AlchemyTaskRunConnector
from affiche.app.task_history.model.task_run import TaskRun, TaskRunSearch

class TaskHistoryRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyTaskRunConnector(session)

    def save(self, run: TaskRun) -> TaskRun:
        return self._connector.save(run)

    def find_recent(self, search: TaskRunSearch) -> List[TaskRun]:
        return self._connector.find_recent(search)

    def count(self) -> int:
        return self._connector.count()

    def prune(self, keep: int) -> int:
        return self._connector.prune(keep)

    def delete_all(self) -> None:
        self._connector.delete_all()
