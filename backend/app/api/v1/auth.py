from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.auth import (
    AuthStatusResponse,
    DevLoginResponse,
    RefreshResponse,
    UserResponse,
)
from app.services import auth_service, google_oauth, token_service

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다"
        )
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰"
        )
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유저를 찾을 수 없습니다"
        )
    return user


@router.get("/login")
def login() -> RedirectResponse:
    return RedirectResponse(google_oauth.build_authorize_url())


@router.get("/callback")
async def callback(
    code: str, session: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    return await auth_service.handle_oauth_callback(code, session)


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    return AuthStatusResponse(connected=True, message="Use /login to authenticate")


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user_dep)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    """httpOnly 쿠키의 refresh token으로 access token 재발급."""
    cookie = request.cookies.get(token_service.REFRESH_COOKIE_NAME, "")
    body, new_refresh = await auth_service.refresh_session(session, cookie)
    token_service.set_refresh_cookie(response, new_refresh)
    return body


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> None:
    cookie = request.cookies.get(token_service.REFRESH_COOKIE_NAME)
    await auth_service.logout(session, cookie)
    token_service.clear_refresh_cookie(response)


@router.post("/dev-login", response_model=DevLoginResponse)
async def dev_login(
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> DevLoginResponse:
    """로컬 개발용 — Google OAuth 없이 즉시 로그인."""
    body, refresh = await auth_service.dev_login(session)
    token_service.set_refresh_cookie(response, refresh)
    return body
