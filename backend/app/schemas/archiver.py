"""Archiver API Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field


class TabContextExtractionMeta(BaseModel):
    """DOM 추출 결과 요약 — 캐시 hit 여부·본문 길이."""

    char_count: int = Field(ge=0, description="추출·캐시된 본문 글자 수")
    is_cached: bool = Field(
        default=False,
        description="익스텐션 DOM 캐시에서 재사용된 본문인지 여부",
    )


class TabContextMeta(BaseModel):
    """SPA·사이트별 라우팅 힌트 — 익스텐션이 URL·추출 맥락에서 채운다."""

    hostname: str = Field(description="활성 탭 URL 호스트명")
    page_kind: Literal["default", "map"] | None = Field(
        default="default",
        description="페이지 유형 힌트 (지도 SPA 등 전용 크롤러 라우팅용)",
    )
    extraction: TabContextExtractionMeta | None = Field(
        default=None,
        description="DOM 본문 추출 메타 (2차 요청·need_dom 이후에만 채워짐)",
    )


class TabContext(BaseModel):
    url: str
    title: str
    body: str | None = Field(
        default=None,
        max_length=5000,
        description="익스텐션 content script가 추출한 활성 탭 가시 DOM 텍스트",
    )
    meta: TabContextMeta | None = Field(
        default=None,
        description="호스트·페이지 유형·추출 메타 (하위 호환 optional)",
    )


class ChatStreamRequest(BaseModel):
    """익스텐션 사이드패널 → 아카이버 스트림 요청 본문."""

    message: str = Field(..., min_length=1, description="사용자 질문 또는 지시")
    context: TabContext | None = Field(
        default=None,
        description="활성 탭 맥락 (URL, 제목, 선택적 DOM 본문)",
    )
    dom_continuation: bool = Field(
        default=False,
        description="NEED_DOM 이후 DOM 본문을 실어 보내는 2차 요청 여부",
    )


class ArchiverSessionSummary(BaseModel):
    """GET /archiver/sessions 응답 항목."""

    session_id: str
    context_title: str
    context_url: str
    last_activity: datetime


class ArchiverChatMessage(BaseModel):
    """GET /archiver/history/{session_id} 응답 항목."""

    id: int
    role: str
    content: str
    created_at: datetime
