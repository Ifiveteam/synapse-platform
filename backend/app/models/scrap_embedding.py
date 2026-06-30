"""스크랩 본문 임베딩 — scraps 1:1 pgvector."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import RAG_EMBEDDING_DIM
from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class ScrapEmbedding(TimestampMixin, Base):
    """스크랩 본문의 OpenAI 임베딩 (1536차원, 코사인 유사도 그래프용)."""

    __tablename__ = "scrap_embeddings"

    scrap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scraps.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(RAG_EMBEDDING_DIM),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_scrap_embeddings_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
