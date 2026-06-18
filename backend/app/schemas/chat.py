"""Chat / Archiver API Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TabContext(BaseModel):
    url: str
    title: str


class ChatStreamRequest(BaseModel):
    """익스텐션 사이드패널 → 아카이버 스트림 요청 본문."""

    message: str = Field(..., min_length=1, description="사용자 질문 또는 지시")
    context: TabContext | None = Field(
        default=None,
        description="활성 탭 맥락 (URL, 제목)",
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
