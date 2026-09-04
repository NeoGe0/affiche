from fastapi import Request
from fastapi.responses import JSONResponse

from affiche.app.asynch.async_task_service import TaskConflictError
from affiche.app.service_configuration.exceptions import (MediaServerCredentialsRejectedError,
                                                          MediaServerNotFoundError,
                                                          MediaServerUnreachableError,
                                                          NoProvidersConfiguredError)
from affiche.app.style_profile.service.style_profile_service import DuplicateProfileNameError
from affiche.config.exceptions.exceptions import LibraryDisabledException, NotFoundError
from affiche.main import app

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": getattr(exc, "message", None) or str(exc)},
    )

@app.exception_handler(MediaServerNotFoundError)
async def media_server_not_found_handler(request: Request, exc: MediaServerNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(MediaServerUnreachableError)
async def media_server_unreachable_handler(request: Request, exc: MediaServerUnreachableError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})

@app.exception_handler(MediaServerCredentialsRejectedError)
async def media_server_credentials_rejected_handler(
        request: Request, exc: MediaServerCredentialsRejectedError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})

@app.exception_handler(LibraryDisabledException)
async def library_disabled_handler(request: Request, exc: LibraryDisabledException):
    return JSONResponse(
        status_code=400,
        content={"detail": getattr(exc, "message", None) or str(exc)},
    )

@app.exception_handler(DuplicateProfileNameError)
async def duplicate_profile_name_handler(request: Request, exc: DuplicateProfileNameError):
    return JSONResponse(
        status_code=409,
        content={"detail": getattr(exc, "message", None) or str(exc)},
    )

@app.exception_handler(NoProvidersConfiguredError)
async def no_providers_configured_handler(request: Request, exc: NoProvidersConfiguredError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )

@app.exception_handler(TaskConflictError)
async def task_conflict_handler(request: Request, exc: TaskConflictError):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "running_task_id": exc.running_task_id},
    )
