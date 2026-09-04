import logging
from typing import Callable, List, TypeVar

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")

def commit_batch_with_fallback(
        session: Session,
        items: List[T],
        build_stmt: Callable[[T], object],
        describe: Callable[[T], str],
) -> None:
    if not items:
        return

    try:
        for item in items:
            session.execute(build_stmt(item))
        session.commit()
        return
    except Exception:
        session.rollback()
        logger.warning("Batch upsert failed; retrying %d items individually", len(items))

    for item in items:
        try:
            session.execute(build_stmt(item))
            session.commit()
        except Exception:
            session.rollback()
            logger.warning("Skipping item %s: upsert failed", describe(item), exc_info=True)
