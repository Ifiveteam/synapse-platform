"""Google OAuth 로직 (외부 통신 + 토큰/유저 영속화).

API 진입점은 `api/v1/auth.py`, orchestration은 `services/auth_service.py`.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_token import UserToken

# ── 상수 ──────────────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/callback"
)

# 로그인은 기본 프로필만 — Drive 권한은 별도 "폴더 연동"(GIS 코드 클라이언트 +
# drive.file)으로 분리. 전체 드라이브(drive.readonly) 요구를 제거해 거부감/심사 부담을 없앤다.
SCOPES = [
    "openid",
    "email",
    "profile",
]

# 폴더 연동용 — 프론트 GIS 코드 클라이언트가 요청하고, 백엔드는 code를 postmessage로 교환.
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"

# YouTube 재생목록 쓰기 — 재생목록 저장용(별도 동의).
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def _client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "")


def _client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "")


# ── 1. 동의 URL 생성 ──────────────────────────


def build_authorize_url(*, state: str | None = None) -> str:
    """구글 OAuth 동의 화면 URL."""
    params = {
        "client_id": _client_id(),
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


# ── 2. 토큰 교환 / 유저 조회 ──────────────────


async def exchange_code_for_tokens(code: str) -> dict:
    """authorization code → 구글 토큰(access/refresh)."""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    return res.json()


async def fetch_userinfo(access_token: str) -> dict:
    """구글 access token → 유저 프로필."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    return res.json()


async def exchange_code_postmessage(code: str) -> dict:
    """GIS 코드 클라이언트(popup) code → 토큰.

    팝업 흐름은 redirect_uri="postmessage"로 교환한다(서버 redirect 없음).
    로그인 redirect 흐름의 exchange_code_for_tokens와 분리.
    """
    async with httpx.AsyncClient() as client:
        res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "redirect_uri": "postmessage",
                "grant_type": "authorization_code",
            },
        )
    return res.json()


async def store_google_tokens(session: AsyncSession, user: User, tokens: dict) -> None:
    """이미 로그인된 유저의 구글 access/refresh 토큰 저장 (Drive 폴더 연동용).

    refresh_token은 응답에 있을 때만 갱신(재동의 없이는 안 줄 수 있으므로 보존).
    """
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")

    if access:
        user.access_token = access

    result = await session.execute(
        select(UserToken).where(UserToken.user_id == user.id)
    )
    token_row = result.scalar_one_or_none()
    if token_row is None:
        token_row = UserToken(
            user_id=user.id,
            refresh_token="",
            google_refresh_token=refresh,
            expires_at=datetime.now(timezone.utc),
        )
        session.add(token_row)
    elif refresh:
        token_row.google_refresh_token = refresh

    await session.flush()


# ── 3. 영속화 ─────────────────────────────────


async def upsert_user_and_token(
    session: AsyncSession, info: dict, tokens: dict
) -> User:
    """구글 프로필 + 토큰을 users / user_token 테이블에 upsert 후 User 반환.

    - users.access_token        = 구글 access token (Drive/YouTube API용)
    - user_token.google_refresh_token = 구글 refresh token
    - user_token.refresh_token  = 서비스 자체 refresh token (신규 발급)
    """
    google_sub_id = info.get("id")
    if not google_sub_id:
        raise ValueError("google_sub_id_missing")

    google_access = tokens.get("access_token")
    google_refresh = tokens.get("refresh_token")

    # users upsert
    result = await session.execute(
        select(User).where(User.google_sub_id == google_sub_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_sub_id=google_sub_id,
            email=info.get("email", ""),
            name=info.get("name", ""),
            picture=info.get("picture"),
            access_token=google_access,
        )
        session.add(user)
    else:
        user.access_token = google_access
        # name/picture는 사용자가 직접 수정했을 수 있으므로 덮어쓰지 않음

    await session.flush()  # user.id 확보

    # user_token — google_refresh_token만 갱신 (서비스 refresh는 token_service)
    token_result = await session.execute(
        select(UserToken).where(UserToken.user_id == user.id)
    )
    token_row = token_result.scalar_one_or_none()

    if token_row is None:
        token_row = UserToken(
            user_id=user.id,
            refresh_token="",
            google_refresh_token=google_refresh,
            expires_at=datetime.now(timezone.utc),
        )
        session.add(token_row)
    else:
        if google_refresh:
            token_row.google_refresh_token = google_refresh

    await session.flush()
    await session.refresh(user)
    return user


# ── 4. 구글 access token 갱신 ─────────────────


async def _token_scopes(access_token: str) -> set[str]:
    """access token의 부여된 스코프 집합 (tokeninfo, 무쿼터). 실패 시 빈 집합."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                GOOGLE_TOKENINFO_URL, params={"access_token": access_token}
            )
        data = res.json()
    except Exception:
        return set()
    return set((data.get("scope") or "").split())


async def get_youtube_access_token(user) -> str | None:
    """youtube 스코프를 포함한 유효 access token. 없거나 스코프 부족이면 None.

    None이면 호출측이 needs_reconsent 처리(사용자 재동의 유도).
    동의 직후 저장된 access_token을 먼저 확인하고(스코프 보유·유효),
    만료 등으로 실패할 때만 refresh 후 재확인한다(재동의 루프 방지).
    """
    token = user.access_token
    if token and YOUTUBE_SCOPE in await _token_scopes(token):
        return token
    refreshed = await refresh_access_token(user)
    if refreshed and YOUTUBE_SCOPE in await _token_scopes(refreshed):
        return refreshed
    return None


async def refresh_access_token(user) -> str | None:
    """user_token.google_refresh_token으로 구글 access token 갱신 후 DB 저장."""
    from app.core.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        token_result = await session.execute(
            select(UserToken).where(UserToken.user_id == user.id)
        )
        token_row = token_result.scalar_one_or_none()
        if token_row is None or not token_row.google_refresh_token:
            return None

        async with httpx.AsyncClient() as client:
            res = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": _client_id(),
                    "client_secret": _client_secret(),
                    "refresh_token": token_row.google_refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        data = res.json()
        new_token = data.get("access_token")
        if not new_token:
            return None

        db_user = await session.get(User, user.id)
        if db_user:
            db_user.access_token = new_token
            await session.commit()

    return new_token
