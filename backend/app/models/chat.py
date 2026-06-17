"""Archiver & Aggregator 확장 대응 통합 AI 채팅 로그 모델."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class AIChatLog(Base):
    __tablename__ = "ai_chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    # 에이전트 확장 대응 코어 필드
    agent_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 아카이버 전용 패시브 웹 맥락 필드 (일반 채팅 시 null 허용)
    context_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    context_title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
