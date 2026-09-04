from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from affiche.api.schemas.dashboard import (
    DashboardResponse,
    DashboardTask,
    ProviderDayResponse,
    ProviderHistoryResponse,
    ProviderShareResponse,
)
from affiche.app.dashboard import DashboardService
from affiche.app.provider_stats import (
    DEFAULT_WINDOW_DAYS,
    RETENTION_DAYS,
    ProviderStatsQuery,
    ProviderStatsService,
)
from affiche.app.task_history import TaskHistoryService, TaskRun, TaskRunSearch
from affiche.config.dependencies import (
    get_dashboard_service,
    get_provider_stats_service,
    get_task_history_service,
)

router = APIRouter()

RECENT_TASK_LIMIT = 10

@router.get("", response_model=DashboardResponse)
def get_dashboard(recent_tasks: int = Query(RECENT_TASK_LIMIT, ge=0, le=50),
                  service: DashboardService = Depends(get_dashboard_service),
                  history: TaskHistoryService = Depends(get_task_history_service)) -> DashboardResponse:
    summary = service.get_summary()
    return DashboardResponse(
        **summary.model_dump(),
        recent_tasks=_recent_tasks(history, recent_tasks),
    )

@router.get("/provider-history", response_model=ProviderHistoryResponse)
def get_provider_history(days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=RETENTION_DAYS),
                         library_id: Optional[int] = None,
                         stats: ProviderStatsService = Depends(get_provider_stats_service),
                         ) -> ProviderHistoryResponse:
    query = ProviderStatsQuery(days=days, library_id=library_id)
    return ProviderHistoryResponse(
        days=days,
        series=[ProviderDayResponse(day=row.day.isoformat(), provider=row.provider, count=row.count)
                for row in stats.daily(query)],
        totals=[ProviderShareResponse(provider=provider, count=count)
                for provider, count in sorted(stats.totals(query).items(),
                                              key=lambda kv: (-kv[1], kv[0]))],
    )

def _recent_tasks(history: TaskHistoryService, limit: int) -> List[DashboardTask]:
    if limit == 0:
        return []
    return [_task_response(run) for run in history.find_recent(TaskRunSearch(page_size=limit))]

def _task_response(run: TaskRun) -> DashboardTask:
    return DashboardTask(
        task_id=run.task_id,
        task_name=run.task_name,
        status=run.status,
        created_at=run.created_at.isoformat(),
        completed_at=run.ended_at.isoformat() if run.ended_at else None,
        message=run.message,
        error=run.error,
    )
