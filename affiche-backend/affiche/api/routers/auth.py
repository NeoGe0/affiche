import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from typing import List

from affiche.api.schemas.auth_schema import (
    AuthStatusResponse,
    ChangePasswordRequest,
    CreateUserRequest,
    UpdateUserRequest,
    LoginRequest,
    SetupRequest,
    UserAccountResponse,
    UserResponse,
)
from affiche.app.auth.model.user import User
from affiche.app.auth.service.auth_service import (
    AuthError,
    AuthService,
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
)
from affiche.config.dependencies import get_auth_service, get_current_user, require_admin

router = APIRouter()

logger = logging.getLogger(__name__)

FAILED_LOGIN_DELAY_SECONDS = 3.0

def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )

@router.get("/status", response_model=AuthStatusResponse)
def auth_status(
        affiche_session: Optional[str] = Cookie(default=None),
        service: AuthService = Depends(get_auth_service),
):
    user = service.user_from_token(affiche_session)
    return AuthStatusResponse(
        setup_required=not service.has_admin(),
        authenticated=user is not None,
        username=user.username if user else None,
        role=user.role if user else None,
        password_change_required=bool(user and user.password_temporary),
    )

@router.post("/setup", response_model=UserResponse)
def setup_admin(
        payload: SetupRequest,
        request: Request,
        response: Response,
        service: AuthService = Depends(get_auth_service),
):
    try:
        user = service.create_admin(payload.username, payload.password)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _set_session_cookie(response, request, service.issue_token(user))
    return UserResponse(username=user.username, role=user.role)

@router.post("/login", response_model=UserResponse)
async def login(
        payload: LoginRequest,
        request: Request,
        response: Response,
        service: AuthService = Depends(get_auth_service),
):
    user = await run_in_threadpool(service.authenticate, payload.username, payload.password)
    if user is None:
        await asyncio.sleep(FAILED_LOGIN_DELAY_SECONDS)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    _set_session_cookie(response, request, service.issue_token(user))
    return UserResponse(username=user.username, role=user.role,
                        password_change_required=user.password_temporary)

@router.post("/password", response_model=UserResponse)
async def change_password(
        payload: ChangePasswordRequest,
        request: Request,
        response: Response,
        affiche_session: Optional[str] = Cookie(default=None),
        service: AuthService = Depends(get_auth_service),
):
    user = await run_in_threadpool(service.user_from_token, affiche_session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        updated = await run_in_threadpool(
            service.change_password, user, payload.current_password, payload.new_password)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _set_session_cookie(response, request, service.issue_token(updated))
    return UserResponse(username=updated.username, role=updated.role,
                        password_change_required=updated.password_temporary)

@router.post("/logout")
def logout(response: Response,
           affiche_session: Optional[str] = Cookie(default=None),
           service: AuthService = Depends(get_auth_service)):
    service.revoke_sessions(affiche_session)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(username=user.username, role=user.role,
                        password_change_required=user.password_temporary)

def _account(user: User) -> UserAccountResponse:
    return UserAccountResponse(id=user.id, username=user.username, role=user.role,
                               password_change_required=user.password_temporary)

@router.get("/users", response_model=List[UserAccountResponse])
def list_users(_: User = Depends(require_admin),
               service: AuthService = Depends(get_auth_service)):
    return [_account(user) for user in service.list_users()]

@router.post("/users", response_model=UserAccountResponse, status_code=201)
async def create_user(payload: CreateUserRequest,
                      _: User = Depends(require_admin),
                      service: AuthService = Depends(get_auth_service)):
    try:
        user = await run_in_threadpool(
            service.create_user, payload.username, payload.password, payload.role)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("Created account %r (%s)", user.username, user.role.value)
    return _account(user)

@router.patch("/users/{user_id}", response_model=UserAccountResponse)
def update_user(user_id: int,
                payload: UpdateUserRequest,
                acting_user: User = Depends(require_admin),
                service: AuthService = Depends(get_auth_service)):
    try:
        return _account(service.set_role(user_id, payload.role, acting_user))
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int,
                acting_user: User = Depends(require_admin),
                service: AuthService = Depends(get_auth_service)):
    try:
        service.delete_user(user_id, acting_user)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
