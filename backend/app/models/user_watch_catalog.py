from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base

if TYPE_CHECKING:
    from app.models.video_analysis import VideoAnalysis

EMBEDDING_DIM = 1536


class UserWatchCatalog(Base):
    """Takeout 2개월 시청 정본. 영상(URL) 단위 1행 — 인덱서 유일 영속 결과."""

    __tablename__ = "user_watch_catalog"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    channel_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    watch_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )  # 분석 윈도우 내 반복 시청 횟수 (선호 강도)

    youtube_category_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_shorts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )

    analysis: Mapped[VideoAnalysis | None] = relationship(
        "VideoAnalysis",
        back_populates="catalog",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "url", name="uq_uwc_user_url"),
        Index("ix_uwc_user_watched", text("user_id"), text("watched_at DESC")),
        Index("ix_uwc_user_category", "user_id", "youtube_category_id"),
        Index(
            "ix_uwc_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
