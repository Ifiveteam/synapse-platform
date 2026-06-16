from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db
from app.core.security import create_access_token, decode_access_token
from app.models.user import User
from app.services import google_oauth

router = APIRouter(prefix="/auth", tags=["auth"])


def _frontend_url() -> str:
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")


# ── Google OAuth ──────────────────────────────


@router.get("/login")
def login():
    return RedirectResponse(google_oauth.build_authorize_url())


@router.get("/callback")
async def callback(code: str, session: AsyncSession = Depends(get_db)):
    # 1. 코드 → 구글 토큰 교환
    tokens = await google_oauth.exchange_code_for_tokens(code)
    if "access_token" not in tokens:
        raise HTTPException(status_code=400, detail="Google 토큰 발급 실패")

    # 2. 유저 정보 조회
    info = await google_oauth.fetch_userinfo(tokens["access_token"])
    if not info.get("id"):
        raise HTTPException(status_code=400, detail="Google 유저 정보 조회 실패")

    # 3. users / user_token upsert
    user = await google_oauth.upsert_user_and_token(session, info, tokens)

    # 4. JWT 발급 → 프론트로 리디렉트
    jwt_token = create_access_token(user.id)
    return RedirectResponse(f"{_frontend_url()}/upload?token={jwt_token}")


@router.get("/status")
async def auth_status():
    return {"connected": True, "message": "Use /login to authenticate"}


# ── 현재 유저 조회 (FastAPI dependency) ────────

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
    id: uuid.UUID
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
    google_sub_id = "dev-local-user"
    result = await session.execute(
        select(User).where(User.google_sub_id == google_sub_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_sub_id=google_sub_id,
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
