from sqlalchemy.pool import QueuePool

from affiche.config.database import (
    MAX_OVERFLOW, POOL_SIZE, POOL_TIMEOUT_SECONDS, engine,
)
from affiche.app.asynch.async_task_service import AsyncTaskService
from affiche.app.mediaserver.service.poster_workers import MAX_WORKERS, RESET_MAX_WORKERS

REQUEST_THREADPOOL = 40

BACKGROUND_SINGLETONS = 2

def test_the_pool_clears_the_worst_case_number_of_borrowers():
    detached_tasks = AsyncTaskService()._executor._max_workers
    worst_case = (
        REQUEST_THREADPOOL
        + MAX_WORKERS
        + RESET_MAX_WORKERS
        + detached_tasks
        + BACKGROUND_SINGLETONS
    )

    assert POOL_SIZE + MAX_OVERFLOW >= worst_case

def test_the_engine_actually_uses_those_numbers():
    assert isinstance(engine.pool, QueuePool)
    assert engine.pool.size() == POOL_SIZE
    assert engine.pool._max_overflow == MAX_OVERFLOW

def test_exhaustion_fails_faster_than_the_default_thirty_seconds():
    assert engine.pool._timeout == POOL_TIMEOUT_SECONDS
    assert POOL_TIMEOUT_SECONDS < 30

def test_sqlite_does_not_pay_for_pre_ping():
    from affiche.config.database import IS_SQLITE

    assert engine.pool._pre_ping is not IS_SQLITE
