import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.model import LibrarySearch
from affiche.app.asynch.async_task_service import AsyncTaskService, TaskConflictError
from affiche.app.asynch.library_tasks import sync_library_posters_task, sync_library_task
from affiche.app.mediaserver.library.settings.model.library_settings import AutoPickupAction
from affiche.app.mediaserver.library.sync.incremental import may_run_incrementally
from affiche.app.mediaserver.model.media_server import MediaServer
from affiche.config.dependencies import container

logger = logging.getLogger(__name__)

def dispatch_library_pickup(
        task_service: AsyncTaskService,
        media_server_id: int,
        library_id: int,
        action: AutoPickupAction,
        incremental: bool = False,
) -> Optional[Tuple[str, str]]:
    action = AutoPickupAction(action)

    if action == AutoPickupAction.SYNC:
        task_func = (lambda cancel_check=None:
                     sync_library_task(media_server_id, library_id, cancel_check=cancel_check,
                                       incremental=incremental))
        task_name = f"library_sync_{media_server_id}_{library_id}"
    else:
        upload = action == AutoPickupAction.UPLOAD
        task_func = (lambda cancel_check=None:
                     sync_library_posters_task(media_server_id, library_id,
                                               cancel_check=cancel_check, upload=upload,
                                               incremental=incremental))
        task_name = f"poster_sync_{library_id}"

    resource = f"ms:{media_server_id}:lib:{library_id}"
    try:
        return task_service.submit_detached_task(
            task_func=task_func, task_name=task_name, blocking=True, resource=resource)
    except TaskConflictError as e:
        logger.info("Auto-pickup for library %d skipped — conflicting task %s running",
                    library_id, e.running_task_id)
        return None

def pickup_for_new_item(session: Session,
                        server: MediaServer,
                        library_external_id: Optional[str],
                        *,
                        dispatch: bool = True) -> List[dict]:
    libraries = [lib for lib in container.library_service(session)
                 .find_libraries(LibrarySearch(media_server_id=server.id))
                 if lib.enabled]

    targets = []
    if library_external_id:
        match = next((lib for lib in libraries
                      if str(lib.external_id) == str(library_external_id)), None)
        if match:
            targets = [match]
        else:
            logger.info("Webhook: payload library id %s didn't match a synced library — "
                        "falling back to all %d enabled libraries",
                        library_external_id, len(libraries))
    if not targets:
        targets = libraries

    settings_service = container.library_settings_service(session)
    task_service = container.async_task_service
    results = []
    for lib in targets:
        settings = settings_service.get_settings_or_default(lib.id)
        action = settings.auto_pickup_action
        action_str = action.value if hasattr(action, "value") else action
        incremental = may_run_incrementally(settings.last_full_sync_at,
                                            datetime.now(timezone.utc))
        if dispatch:
            if dispatch_library_pickup(task_service, server.id, lib.id, action,
                                       incremental=incremental) is not None:
                results.append({"id": lib.id, "name": lib.name, "action": action_str})
                logger.info("Webhook pickup dispatched: library '%s' (id=%d, action=%s)",
                            lib.name, lib.id, action_str)
        else:
            results.append({"id": lib.id, "name": lib.name, "action": action_str})
            logger.info("Webhook TEST (dry-run): would dispatch library '%s' (id=%d, action=%s)",
                        lib.name, lib.id, action_str)

    if not results:
        logger.info("Webhook new-item event matched no dispatchable library "
                    "(no enabled libraries%s)",
                    "" if not dispatch else ", or all had a conflicting task running")
    return results
