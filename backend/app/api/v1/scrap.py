"""Scrap API 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.auth import get_current_user_dep
from app.models.user import User
from app.schemas.scrap import ScrapCreateRequest
from app.schemas.scrap_graph import ScrapGraphResponse
from app.services.archiver_service import ArchiverService
from app.services.scrap_graph_service import ScrapGraphService

router = APIRouter(prefix="/scraps", tags=["Scrap"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scrap(
    request: ScrapCreateRequest,
    user: User = Depends(get_current_user_dep),
    archiver_service: ArchiverService = Depends(),
) -> dict[str, object]:
    """웹 페이지 본문을 Gemini로 요약·분류하여 스크랩을 생성한다."""
    scrap = await archiver_service.create_scrap_pipeline(
        user_id=user.id,
        request_data=request,
    )
    return {
        "status": "success",
        "data": scrap.model_dump(mode="json"),
    }


@router.get("/graph", response_model=ScrapGraphResponse)
async def get_scrap_graph(
    categories: str | None = Query(
        default=None,
        description="쉼표 구분 카테고리 필터 (예: 기술,경제)",
    ),
    tags: str | None = Query(
        default=None,
        description="쉼표 구분 태그 필터 — 하나라도 포함된 노드만 (예: AI,Python)",
    ),
    user: User = Depends(get_current_user_dep),
    graph_service: ScrapGraphService = Depends(),
) -> ScrapGraphResponse:
    """로그인 유저의 스크랩 임베딩 그래프 nodes·links를 반환한다."""
    return await graph_service.get_graph(
        user_id=user.id,
        categories=categories,
        tags=tags,
    )


@router.get("")
async def list_scraps(
    user: User = Depends(get_current_user_dep),
    archiver_service: ArchiverService = Depends(),
) -> dict[str, object]:
    """현재 로그인한 유저의 스크랩 목록을 최신순으로 반환한다."""
    scraps = await archiver_service.get_user_scraps(user_id=user.id)
    return {
        "status": "success",
        "data": [item.model_dump(mode="json") for item in scraps],
    }


@router.get("/{scrap_id}")
async def get_scrap(
    scrap_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    archiver_service: ArchiverService = Depends(),
) -> dict[str, object]:
    """본인 소유 스크랩 1건과 URL 기준 Archiver 대화 히스토리를 반환한다."""
    detail = await archiver_service.get_user_scrap_detail(
        user_id=user.id,
        scrap_id=scrap_id,
    )
    return {
        "status": "success",
        "data": detail.model_dump(mode="json"),
    }


@router.delete("/{scrap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scrap(
    scrap_id: uuid.UUID,
    user: User = Depends(get_current_user_dep),
    archiver_service: ArchiverService = Depends(),
) -> None:
    """본인 소유 스크랩 1건을 삭제한다."""
    await archiver_service.delete_user_scrap(user_id=user.id, scrap_id=scrap_id)
