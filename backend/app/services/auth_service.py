"""인증 orchestration — OAuth 콜백·개발 로그인·세션 갱신."""

from __future__ import annotations

import base64
import json
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import DevLoginResponse, RefreshResponse, UserResponse
from app.services import extension_auth_service, google_oauth, token_service

DEV_GOOGLE_SUB_ID = "dev-local-user"


def frontend_url() -> str:
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


def encode_oauth_state(payload: dict[str, str]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_oauth_state(state: str) -> dict[str, str]:
    padding = "=" * (-len(state) % 4)
    raw = base64.urlsafe_b64decode(state + padding)
    data = json.loads(raw.decode())
    if not isinstance(data, dict):
        raise ValueError("invalid_oauth_state")
    return {str(k): str(v) for k, v in data.items()}


def is_allowed_extension_redirect_uri(redirect_uri: str) -> bool:
    """chrome.identity.getRedirectURL() 또는 chrome-extension:// 콜백만 허용."""
    parsed = urlparse(redirect_uri)
    if parsed.scheme == "chrome-extension" and parsed.netloc:
        return True
    if (
        parsed.scheme == "https"
        and parsed.hostname
        and parsed.hostname.endswith(".chromiumapp.org")
    ):
        return True
    return False


def append_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query[key] = value
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query),
            parsed.fragment,
        )
    )


def build_extension_login_url(redirect_uri: str) -> str:
    if not is_allowed_extension_redirect_uri(redirect_uri):
        raise HTTPException(status_code=400, detail="허용되지 않은 redirect_uri")

    state = encode_oauth_state({"flow": "extension", "redirect_uri": redirect_uri})
    return google_oauth.build_authorize_url(state=state)


async def handle_oauth_callback(
    code: str,
    state: str | None,
    session: AsyncSession,
) -> RedirectResponse:
    tokens = await google_oauth.exchange_code_for_tokens(code)
    if "access_token" not in tokens:
        raise HTTPException(status_code=400, detail="Google 토큰 발급 실패")

    info = await google_oauth.fetch_userinfo(tokens["access_token"])
    if not info.get("id"):
        raise HTTPException(status_code=400, detail="Google 유저 정보 조회 실패")

    user = await google_oauth.upsert_user_and_token(session, info, tokens)

    if state:
        try:
            payload = decode_oauth_state(state)
            if payload.get("flow") == "extension":
                redirect_uri = payload.get("redirect_uri", "")
                if is_allowed_extension_redirect_uri(redirect_uri):
                    link_code, _ = (
                        await extension_auth_service.create_extension_link_code(
                            session, user.id
                        )
                    )
                    await session.commit()
                    return RedirectResponse(
                        append_query_param(redirect_uri, "code", link_code)
                    )
        except (ValueError, json.JSONDecodeError):
            pass

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
    user: User | None = None
    if refresh_token:
        user = await token_service.find_user_by_refresh_token(session, refresh_token)
        await token_service.revoke_refresh_token(session, refresh_token)

    if user is not None:
        await extension_auth_service.revoke_extension_refresh_for_user(
            session, user.id
        )

    await session.commit()
