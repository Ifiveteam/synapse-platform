from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_token import UserToken

REFRESH_COOKIE_NAME = "synapse_refresh"
REFRESH_EXPIRE_DAYS = 30


def _cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "").lower() in {"1", "true", "yes"}


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=REFRESH_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )


async def issue_refresh_token(session: AsyncSession, user_id: uuid.UUID) -> str:
    """서비스 refresh token 발급·DB 저장 후 평문 반환 (쿠키용)."""
    plain = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)

    result = await session.execute(
        select(UserToken).where(UserToken.user_id == user_id)
    )
    token_row = result.scalar_one_or_none()

    if token_row is None:
        token_row = UserToken(
            user_id=user_id,
            refresh_token=plain,
            expires_at=expires_at,
        )
        session.add(token_row)
    else:
        token_row.refresh_token = plain
        token_row.expires_at = expires_at

    await session.flush()
    return plain


async def find_user_by_refresh_token(
    session: AsyncSession, refresh_token: str
) -> User | None:
    if not refresh_token:
        return None

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(User, UserToken)
        .join(UserToken, UserToken.user_id == User.id)
        .where(
            UserToken.refresh_token == refresh_token,
            UserToken.expires_at > now,
        )
    )
    row = result.first()
    if row is None:
        return None
    user, _ = row
    return user


async def revoke_refresh_token(session: AsyncSession, refresh_token: str) -> None:
    if not refresh_token:
        return

    result = await session.execute(
        select(UserToken).where(UserToken.refresh_token == refresh_token)
    )
    token_row = result.scalar_one_or_none()
    if token_row is None:
        return

    token_row.refresh_token = secrets.token_urlsafe(32)
    token_row.expires_at = datetime.now(timezone.utc)
