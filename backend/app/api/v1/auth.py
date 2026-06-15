from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db
from app.core.security import create_access_token, decode_access_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback"


def _client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "")


def _client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "")


def _frontend_url() -> str:
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")


SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive.readonly",
]


# ── Google OAuth ──────────────────────────────


@router.get("/login")
def login():
    params = {
        "client_id": _client_id(),
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(code: str, session: AsyncSession = Depends(get_db)):
    # 1. 코드 → 토큰 교환
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    tokens = token_res.json()
    if "access_token" not in tokens:
        raise HTTPException(status_code=400, detail="Google 토큰 발급 실패")

    # 2. 유저 정보 조회
    async with httpx.AsyncClient() as client:
        info_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
    info = info_res.json()
    google_id = info.get("id")
    if not google_id:
        raise HTTPException(status_code=400, detail="Google 유저 정보 조회 실패")

    # 3. DB upsert
    result = await session.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_id=google_id,
            email=info.get("email", ""),
            name=info.get("name", ""),
            picture=info.get("picture"),
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
        )
        session.add(user)
    else:
        user.access_token = tokens.get("access_token")
        if tokens.get("refresh_token"):
            user.refresh_token = tokens["refresh_token"]
        user.name = info.get("name", user.name)
        user.picture = info.get("picture", user.picture)

    await session.flush()
    await session.refresh(user)

    # 4. JWT 발급 → 프론트로 리디렉트
    jwt_token = create_access_token(user.id)
    return RedirectResponse(f"{_frontend_url()}/agents/indexer?token={jwt_token}")


@router.get("/status")
async def auth_status():
    return {"connected": True, "message": "Use /login to authenticate"}


# ── 현재 유저 조회 (FastAPI dependency) ────────


async def get_current_user(
    authorization: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> User:
    raise HTTPException(status_code=501, detail="Use get_current_user_dep")


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


# ── Me 엔드포인트 ─────────────────────────────


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None

    model_config = {"from_attributes": True}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user_dep)) -> UserResponse:
    return UserResponse.model_validate(user)


class DevLoginResponse(BaseModel):
    access_token: str
    user: UserResponse


@router.post("/dev-login", response_model=DevLoginResponse)
async def dev_login(session: AsyncSession = Depends(get_db)):
    """로컬 개발용 — Google OAuth 없이 즉시 로그인."""
    google_id = "dev-local-user"
    result = await session.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_id=google_id,
            email="dev@synapse.local",
            name="Synapse Dev",
            picture=None,
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)

    token = create_access_token(user.id)
    return DevLoginResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
