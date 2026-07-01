from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin

if TYPE_CHECKING:
    from app.models.user_watch_catalog import UserWatchCatalog

EMBEDDING_DIM = 1536


class VideoAnalysis(TimestampMixin, Base):
    """프로파일러 영상 의미 분석 (catalog 1:1)."""

    __tablename__ = "video_analysis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_watch_catalog.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    summary_kr: Mapped[str] = mapped_column(Text, nullable=False)
    tones: Mapped[list] = mapped_column(JSONB, nullable=False)
    intents: Mapped[list] = mapped_column(JSONB, nullable=False)
    value_signals: Mapped[list] = mapped_column(JSONB, nullable=False)
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=False
    )

    catalog: Mapped[UserWatchCatalog] = relationship(
        "UserWatchCatalog",
        back_populates="analysis",
    )

    __table_args__ = (
        Index("ix_va_user", "user_id"),
        Index(
            "ix_va_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
