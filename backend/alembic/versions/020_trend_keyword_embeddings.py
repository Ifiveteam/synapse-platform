"""add trend_keyword_embeddings + snapshot semantic_links

Reporter Semantic Link Phase 1:
- 키워드 벡터 캐시 테이블 (pgvector HNSW)
- global_trends_snapshot.semantic_links JSONB

Revision ID: 020_trend_keyword_embeddings
Revises: f49e66b1872d
Create Date: 2026-07-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "020_trend_keyword_embeddings"
down_revision: str | Sequence[str] | None = "f49e66b1872d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trend_keyword_embeddings",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(length=256), nullable=False),
        sa.Column(
            "hint_source",
            sa.String(length=32),
            nullable=False,
            comment="scrap|youtube|behavior|external|mixed",
        ),
        sa.Column(
            "hint_domain",
            sa.String(length=64),
            nullable=False,
            comment="TrendDomain.value 예: Tech/Business",
        ),
        sa.Column(
            "embedding_text",
            sa.Text(),
            nullable=False,
            comment='힌트 결합 임베딩 입력 예: "[behavior|Economy/TechFin] 금리"',
        ),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column(
            "model",
            sa.String(length=64),
            server_default=sa.text("'text-embedding-3-small'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("embedding_text", name="uq_tke_embedding_text"),
    )
    op.create_index(
        "ix_trend_keyword_embeddings_keyword",
        "trend_keyword_embeddings",
        ["keyword"],
        unique=False,
    )
    op.create_index(
        "ix_tke_keyword_domain",
        "trend_keyword_embeddings",
        ["keyword", "hint_domain"],
        unique=False,
    )
    op.create_index(
        "ix_tke_embedding",
        "trend_keyword_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.add_column(
        "global_trends_snapshot",
        sa.Column(
            "semantic_links",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment=(
                "당일 키워드 semantic edges: "
                "[{source,target,similarity,link_type,left_hint,right_hint}]"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("global_trends_snapshot", "semantic_links")
    op.drop_index(
        "ix_tke_embedding",
        table_name="trend_keyword_embeddings",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_index("ix_tke_keyword_domain", table_name="trend_keyword_embeddings")
    op.drop_index(
        "ix_trend_keyword_embeddings_keyword",
        table_name="trend_keyword_embeddings",
    )
    op.drop_table("trend_keyword_embeddings")
