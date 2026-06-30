from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db
from app.core.security import create_access_token, decode_access_token
from app.models.user import User
from app.schemas.auth import (
    AuthStatusResponse,
    DevLoginResponse,
    DriveConnectRequest,
    DriveConnectResponse,
    ExtensionCodeResponse,
    ExtensionExchangeRequest,
    ExtensionRefreshRequest,
    ExtensionRevokeRequest,
    ExtensionSessionResponse,
    RefreshResponse,
    UpdateMeRequest,
    UserResponse,
)
from app.services import (
    auth_service,
    extension_auth_service,
    google_oauth,
    token_service,
)

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


async def get_web_session_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    """웹 access Bearer 또는 httpOnly refresh 쿠키로 인증된 유저."""
    if credentials and credentials.credentials:
        user_id = decode_access_token(credentials.credentials)
        if user_id:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                return user

    cookie = request.cookies.get(token_service.REFRESH_COOKIE_NAME, "")
    if cookie:
        user = await token_service.find_user_by_refresh_token(session, cookie)
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다"
    )


@router.get("/login")
def login() -> RedirectResponse:
    return RedirectResponse(google_oauth.build_authorize_url())


@router.get("/extension/login")
def extension_login(redirect_uri: str) -> RedirectResponse:
    """익스텐션 chrome.identity.launchWebAuthFlow 진입점."""
    return RedirectResponse(auth_service.build_extension_login_url(redirect_uri))


@router.get("/callback")
async def callback(
    code: str | None = None,
    error: str | None = None,
    state: str = "",
    session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    return await auth_service.handle_oauth_callback(
        code=code,
        error=error,
        state=state or None,
        session=session,
    )


@router.post("/drive/connect", response_model=DriveConnectResponse)
async def drive_connect(
    body: DriveConnectRequest,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> DriveConnectResponse:
    """GIS 코드 클라이언트 code → drive.file 토큰 저장 + Picker용 access token 반환.

    이후 프론트는 받은 access_token으로 Picker를 띄워 폴더를 선택한다(계정 정렬).
    """
    tokens = await google_oauth.exchange_code_postmessage(body.code)
    access = tokens.get("access_token")
    if not access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="drive_token_exchange_failed",
        )
    await google_oauth.store_google_tokens(session, user, tokens)
    await session.commit()
    return DriveConnectResponse(access_token=access)


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    return AuthStatusResponse(connected=True, message="Use /login to authenticate")


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user_dep)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> None:
    await session.delete(user)
    await session.commit()
    token_service.clear_refresh_cookie(response)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateMeRequest,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    if body.nickname is not None:
        user.name = body.nickname
    if body.picture is not None:
        user.picture = body.picture
    session.add(user)
    await session.commit()
    await session.refresh(user)
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


@router.post("/extension-code", response_model=ExtensionCodeResponse)
async def issue_extension_code(
    user: User = Depends(get_web_session_user),
    session: AsyncSession = Depends(get_db),
) -> ExtensionCodeResponse:
    """웹 로그인 세션 → 익스텐션 1회용 연동 code 발급."""
    code, expires_in = await extension_auth_service.create_extension_link_code(
        session, user.id
    )
    await session.commit()
    return ExtensionCodeResponse(code=code, expires_in=expires_in)


@router.post("/extension-exchange", response_model=ExtensionSessionResponse)
async def exchange_extension_code(
    body: ExtensionExchangeRequest,
    session: AsyncSession = Depends(get_db),
) -> ExtensionSessionResponse:
    """1회용 code → extension access + refresh token."""
    return await extension_auth_service.exchange_extension_code(session, body.code)


@router.post("/extension-refresh", response_model=ExtensionSessionResponse)
async def refresh_extension_session(
    body: ExtensionRefreshRequest,
    session: AsyncSession = Depends(get_db),
) -> ExtensionSessionResponse:
    """extension refresh token으로 access 재발급 (rotation)."""
    return await extension_auth_service.refresh_extension_session(
        session, body.refresh_token
    )


@router.post("/extension-revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_extension_session(
    body: ExtensionRevokeRequest,
    session: AsyncSession = Depends(get_db),
) -> None:
    """익스텐션 refresh token 무효화."""
    await extension_auth_service.revoke_extension_session(session, body.refresh_token)


@router.post("/extension-dev-login", response_model=ExtensionSessionResponse)
async def extension_dev_login(
    session: AsyncSession = Depends(get_db),
) -> ExtensionSessionResponse:
    """로컬 개발용 — 익스텐션 단독 테스트 시 extension refresh 포함 세션 발급."""
    user = await auth_service.get_or_create_dev_user(session)
    refresh = await extension_auth_service.issue_extension_refresh_token(
        session, user.id
    )
    await session.commit()
    access = create_access_token(user.id)
    return extension_auth_service.build_extension_session_response(
        user, access, refresh
    )


@router.post("/dev-login", response_model=DevLoginResponse)
async def dev_login(
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> DevLoginResponse:
    """로컬 개발용 — Google OAuth 없이 즉시 로그인."""
    body, refresh = await auth_service.dev_login(session)
    token_service.set_refresh_cookie(response, refresh)
    return body
