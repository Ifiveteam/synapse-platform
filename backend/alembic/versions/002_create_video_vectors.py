"""Create video_vectors table.

Revision ID: 002_create_video_vectors
Revises: 001_enable_vector
Create Date: 2026-06-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "002_create_video_vectors"
down_revision: str | Sequence[str] | None = "001_enable_vector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "video_vectors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text()),
        sa.Column("channel_url", sa.Text()),
        sa.Column("url", sa.Text(), unique=True),
        sa.Column("watched_at", sa.DateTime()),
        sa.Column("category", sa.Text()),
        sa.Column("keywords", sa.ARRAY(sa.String())),
        sa.Column("duration", sa.Integer()),
        sa.Column("is_shorts", sa.Boolean()),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
    )


def downgrade() -> None:
    op.drop_table("video_vectors")
