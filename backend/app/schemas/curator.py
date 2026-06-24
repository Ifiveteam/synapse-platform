"""Curator API Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CuratorChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="사용자 질문")
    session_id: str | None = Field(default=None, description="대화 세션 ID (없으면 신규)")


class CuratorSessionItem(BaseModel):
    session_id: str
    title: str
    updated_at: datetime


class CuratorSessionListResponse(BaseModel):
    sessions: list[CuratorSessionItem]


class CuratorMessageItem(BaseModel):
    role: str
    content: str


class CuratorSessionMessagesResponse(BaseModel):
    messages: list[CuratorMessageItem]
