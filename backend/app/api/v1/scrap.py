"""Scrap API 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.auth import get_current_user_dep
from app.models.user import User
from app.schemas.scrap import ScrapCreateRequest
from app.services.scrap_service import ScrapService

router = APIRouter(prefix="/scraps", tags=["Scrap"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scrap(
    request: ScrapCreateRequest,
    user: User = Depends(get_current_user_dep),
    scrap_service: ScrapService = Depends(),
) -> dict[str, object]:
    """웹 본문 또는 채팅 맥락을 Gemini로 요약·분류하여 스크랩을 생성한다."""
    scrap = await scrap_service.create_scrap_pipeline(
        user_id=user.id,
        request_data=request,
    )
    return {
        "status": "success",
        "data": scrap.model_dump(mode="json"),
    }


@router.get("")
async def list_scraps(
    user: User = Depends(get_current_user_dep),
    scrap_service: ScrapService = Depends(),
) -> dict[str, object]:
    """현재 로그인한 유저의 스크랩 목록을 최신순으로 반환한다."""
    scraps = await scrap_service.get_user_scraps(user_id=user.id)
    return {
        "status": "success",
        "data": [item.model_dump(mode="json") for item in scraps],
    }


@router.delete("/{scrap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scrap(
    scrap_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    scrap_service: ScrapService = Depends(),
) -> None:
    """본인 소유 스크랩 1건을 삭제한다."""
    await scrap_service.delete_user_scrap(user_id=user.id, scrap_id=scrap_id)
