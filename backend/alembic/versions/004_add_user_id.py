"""Add user_id to video_vectors.

Revision ID: 004_add_user_id
Revises: 003_add_weight
Create Date: 2026-06-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004_add_user_id"
down_revision: str | Sequence[str] | None = "003_add_weight"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "video_vectors",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_video_vectors_user_id", "video_vectors", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_video_vectors_user_id", table_name="video_vectors")
    op.drop_column("video_vectors", "user_id")
