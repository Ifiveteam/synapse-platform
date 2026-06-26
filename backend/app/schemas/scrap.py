"""Scrap API Pydantic 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ScrapSourceType = Literal["web", "chat"]


class ScrapCreateRequest(BaseModel):
    """익스텐션 → 스크랩 파이프라인 생성 요청 본문 (Gemini 전처리 입력)."""

    source_type: ScrapSourceType = Field(
        ...,
        description="수집 경로 — web: FAB·페이지 본문, chat: 대화 맥락",
    )
    url: str | None = Field(
        default=None,
        max_length=2048,
        description="원본 페이지 URL (web 출처 시 권장)",
    )
    title: str | None = Field(
        default=None,
        max_length=512,
        description="페이지 제목 또는 대화 맥락 제목",
    )
    raw_body: str | None = Field(
        default=None,
        max_length=5000,
        description="수집된 원본 텍스트 (Archiver TabContext.body와 동일 한도)",
    )
    session_id: str | None = Field(
        default=None,
        max_length=50,
        description="chat 출처일 때 Archiver 세션 ID",
    )

    @model_validator(mode="after")
    def validate_source_fields(self) -> ScrapCreateRequest:
        if self.source_type == "chat" and not (self.session_id or "").strip():
            msg = "chat 출처 스크랩은 session_id가 필요합니다."
            raise ValueError(msg)
        if self.source_type == "web" and not (self.raw_body or "").strip():
            msg = "web 출처 스크랩은 raw_body가 필요합니다."
            raise ValueError(msg)
        return self


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
