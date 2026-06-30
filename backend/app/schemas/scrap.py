"""Scrap API Pydantic 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.archiver import ArchiverChatMessage

ScrapSourceType = Literal["web", "chat"]


class ScrapCreateRequest(BaseModel):
    """익스텐션 → 스크랩 파이프라인 생성 요청 (현재 페이지 본문 전용)."""

    url: str | None = Field(
        default=None,
        max_length=2048,
        description="원본 페이지 URL",
    )
    title: str | None = Field(
        default=None,
        max_length=512,
        description="페이지 제목",
    )
    raw_body: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="수집된 페이지 본문 (Archiver TabContext.body와 동일 한도)",
    )
    custom_category: str | None = Field(
        default=None,
        max_length=512,
        description="유저가 명시한 스크랩 카테고리 — 있으면 Gemini 카테고리 추론을 override",
    )


class ScrapResponse(BaseModel):
    """DB Scrap ORM → API 응답."""

    id: uuid.UUID
    user_id: uuid.UUID
    source_type: ScrapSourceType
    url: str | None
    title: str | None
    summary: str
    category: str
    tags: list[str]
    raw_body_snapshot: str | None
    session_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScrapDetailResponse(BaseModel):
    """GET /scraps/{id} — 스크랩 + 동일 URL Archiver 대화 히스토리."""

    scrap: ScrapResponse
    archiver_session_id: str | None = Field(
        default=None,
        description="스크랩 URL과 정규화 매칭된 Archiver 세션 ID",
    )
    archiver_history: list[ArchiverChatMessage] = Field(
        default_factory=list,
        description="해당 세션의 Archiver 대화 기록 (시간 오름차순)",
    )
