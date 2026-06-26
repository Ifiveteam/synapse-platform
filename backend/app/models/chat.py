"""Archiver & Aggregator 확장 대응 통합 AI 채팅 로그 모델."""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import RAG_EMBEDDING_DIM
from app.core.database.base import Base


class AIChatLog(Base):
    __tablename__ = "ai_chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # 에이전트 확장 대응 코어 필드
    agent_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 아카이버 전용 패시브 웹 맥락 필드 (일반 채팅 시 null 허용)
    context_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    context_title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    content_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(RAG_EMBEDDING_DIM),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_ai_chat_logs_content_embedding",
            "content_embedding",
            postgresql_using="hnsw",
            postgresql_ops={"content_embedding": "vector_cosine_ops"},
        ),
    )
