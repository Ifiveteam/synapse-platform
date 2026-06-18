"""인증 orchestration — OAuth 콜백·개발 로그인·세션 갱신."""

from __future__ import annotations

import os

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import DevLoginResponse, RefreshResponse, UserResponse
from app.services import google_oauth, token_service

DEV_GOOGLE_SUB_ID = "dev-local-user"


def frontend_url() -> str:
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


async def handle_oauth_callback(code: str, session: AsyncSession) -> RedirectResponse:
    tokens = await google_oauth.exchange_code_for_tokens(code)
    if "access_token" not in tokens:
        raise HTTPException(status_code=400, detail="Google 토큰 발급 실패")

    info = await google_oauth.fetch_userinfo(tokens["access_token"])
    if not info.get("id"):
        raise HTTPException(status_code=400, detail="Google 유저 정보 조회 실패")

    user = await google_oauth.upsert_user_and_token(session, info, tokens)
    refresh = await token_service.issue_refresh_token(session, user.id)
    await session.commit()

    response = RedirectResponse(f"{frontend_url()}/upload")
    token_service.set_refresh_cookie(response, refresh)
    return response


async def get_or_create_dev_user(session: AsyncSession) -> User:
    result = await session.execute(
        select(User).where(User.google_sub_id == DEV_GOOGLE_SUB_ID)
    )
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        google_sub_id=DEV_GOOGLE_SUB_ID,
        email="dev@synapse.local",
        name="Synapse Dev",
        picture=None,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def dev_login(session: AsyncSession) -> tuple[DevLoginResponse, str]:
    user = await get_or_create_dev_user(session)
    refresh = await token_service.issue_refresh_token(session, user.id)
    await session.commit()
    access = create_access_token(user.id)
    return (
        DevLoginResponse(
            access_token=access,
            user=UserResponse.model_validate(user),
        ),
        refresh,
    )


async def refresh_session(
    session: AsyncSession, refresh_token: str
) -> tuple[RefreshResponse, str]:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="refresh token이 없습니다")

    user = await token_service.find_user_by_refresh_token(session, refresh_token)
    if user is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 refresh token")

    new_refresh = await token_service.issue_refresh_token(session, user.id)
    await session.commit()
    access = create_access_token(user.id)
    return RefreshResponse(
        access_token=access,
        user=UserResponse.model_validate(user),
    ), new_refresh


async def logout(session: AsyncSession, refresh_token: str | None) -> None:
    if refresh_token:
        await token_service.revoke_refresh_token(session, refresh_token)
        await session.commit()
