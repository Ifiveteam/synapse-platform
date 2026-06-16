from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin

EMBEDDING_DIM = 1536


class VideoAnalysis(TimestampMixin, Base):
    """영상 의미 분석 (user_video_watch 1:1). [프로파일러]"""

    __tablename__ = "video_analysis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_video_watch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_video_watch.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    summary_kr: Mapped[str | None] = mapped_column(Text, nullable=True)
    tones: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    intents: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    value_signals: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_va_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
