"""create scrap_embeddings table

Revision ID: 004_scrap_embeddings
Revises: 003_user_subscription
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "004_scrap_embeddings"
down_revision: str | Sequence[str] | None = "003_user_subscription"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scrap_embeddings",
        sa.Column("scrap_id", sa.UUID(), nullable=False),
        sa.Column("embedding_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["scrap_id"],
            ["scraps.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scrap_id"),
    )
    op.create_index(
        "ix_scrap_embeddings_embedding",
        "scrap_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scrap_embeddings_embedding",
        table_name="scrap_embeddings",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_table("scrap_embeddings")
