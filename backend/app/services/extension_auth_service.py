"""익스텐션 1회용 연동 코드 + extension refresh token 발급·검증."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.extension_auth_code import ExtensionAuthCode
from app.models.user import User
from app.models.user_token import UserToken
from app.schemas.auth import ExtensionSessionResponse, UserResponse

EXTENSION_CODE_TTL_SECONDS = 60
EXTENSION_REFRESH_EXPIRE_DAYS = 30


def _hash_code(plain_code: str) -> str:
    return hashlib.sha256(plain_code.encode()).hexdigest()


async def _get_user_token_row(
    session: AsyncSession, user_id: uuid.UUID
) -> UserToken | None:
    result = await session.execute(
        select(UserToken).where(UserToken.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_extension_link_code(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[str, int]:
    """웹 로그인 세션으로 1회용 code 발급."""
    plain = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=EXTENSION_CODE_TTL_SECONDS
    )
    session.add(
        ExtensionAuthCode(
            user_id=user_id,
            code_hash=_hash_code(plain),
            expires_at=expires_at,
        )
    )
    await session.flush()
    return plain, EXTENSION_CODE_TTL_SECONDS


async def _consume_extension_link_code(
    session: AsyncSession, plain_code: str
) -> User | None:
    if not plain_code.strip():
        return None

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(ExtensionAuthCode).where(
            ExtensionAuthCode.code_hash == _hash_code(plain_code.strip()),
            ExtensionAuthCode.used_at.is_(None),
            ExtensionAuthCode.expires_at > now,
        )
    )
    code_row = result.scalar_one_or_none()
    if code_row is None:
        return None

    code_row.used_at = now
    user = await session.get(User, code_row.user_id)
    return user


async def issue_extension_refresh_token(
    session: AsyncSession, user_id: uuid.UUID
) -> str:
    """익스텐션 전용 refresh token 발급·rotation."""
    plain = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=EXTENSION_REFRESH_EXPIRE_DAYS
    )

    token_row = await _get_user_token_row(session, user_id)
    if token_row is None:
        token_row = UserToken(
            user_id=user_id,
            refresh_token=secrets.token_urlsafe(32),
            expires_at=expires_at,
            extension_refresh_token=plain,
            extension_expires_at=expires_at,
        )
        session.add(token_row)
    else:
        token_row.extension_refresh_token = plain
        token_row.extension_expires_at = expires_at

    await session.flush()
    return plain


async def find_user_by_extension_refresh_token(
    session: AsyncSession, refresh_token: str
) -> User | None:
    if not refresh_token:
        return None

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(User, UserToken)
        .join(UserToken, UserToken.user_id == User.id)
        .where(
            UserToken.extension_refresh_token == refresh_token,
            UserToken.extension_expires_at > now,
        )
    )
    row = result.first()
    if row is None:
        return None
    user, _ = row
    return user


async def revoke_extension_refresh_token(
    session: AsyncSession, refresh_token: str
) -> None:
    if not refresh_token:
        return

    result = await session.execute(
        select(UserToken).where(UserToken.extension_refresh_token == refresh_token)
    )
    token_row = result.scalar_one_or_none()
    if token_row is None:
        return

    token_row.extension_refresh_token = None
    token_row.extension_expires_at = datetime.now(timezone.utc)


async def revoke_extension_refresh_for_user(
    session: AsyncSession, user_id: uuid.UUID
) -> None:
    token_row = await _get_user_token_row(session, user_id)
    if token_row is None:
        return

    token_row.extension_refresh_token = None
    token_row.extension_expires_at = datetime.now(timezone.utc)


def build_extension_session_response(
    user: User, access_token: str, refresh_token: str
) -> ExtensionSessionResponse:
    return ExtensionSessionResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


async def exchange_extension_code(
    session: AsyncSession, code: str
) -> ExtensionSessionResponse:
    user = await _consume_extension_link_code(session, code)
    if user is None:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 연동 코드")

    refresh = await issue_extension_refresh_token(session, user.id)
    await session.commit()
    access = create_access_token(user.id)
    return build_extension_session_response(user, access, refresh)


async def refresh_extension_session(
    session: AsyncSession, refresh_token: str
) -> ExtensionSessionResponse:
    user = await find_user_by_extension_refresh_token(session, refresh_token)
    if user is None:
        raise HTTPException(
            status_code=401, detail="유효하지 않은 extension refresh token"
        )

    new_refresh = await issue_extension_refresh_token(session, user.id)
    await session.commit()
    access = create_access_token(user.id)
    return build_extension_session_response(user, access, new_refresh)


async def revoke_extension_session(
    session: AsyncSession, refresh_token: str
) -> None:
    await revoke_extension_refresh_token(session, refresh_token)
    await session.commit()
