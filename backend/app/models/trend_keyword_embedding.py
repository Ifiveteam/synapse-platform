"""트렌드 키워드 벡터 캐시 — Aggregator semantic link / 향후 검색·추천 공용."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import RAG_EMBEDDING_DIM
from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class TrendKeywordEmbedding(TimestampMixin, Base):
    """힌트 결합 키워드의 OpenAI 임베딩 (1536차원).

    캐시 키는 raw keyword가 아니라 ``embedding_text`` 이다.
    예: ``[behavior|Economy/TechFin] 금리 인상``
    """

    __tablename__ = "trend_keyword_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    keyword: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    hint_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="scrap|youtube|behavior|external|mixed",
    )
    hint_domain: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="TrendDomain.value 예: Tech/Business",
    )
    embedding_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment='힌트 결합 임베딩 입력 예: "[behavior|Economy/TechFin] 금리"',
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(RAG_EMBEDDING_DIM),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=text("'text-embedding-3-small'"),
    )

    __table_args__ = (
        UniqueConstraint("embedding_text", name="uq_tke_embedding_text"),
        Index("ix_tke_keyword_domain", "keyword", "hint_domain"),
        Index(
            "ix_tke_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
