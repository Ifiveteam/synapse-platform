"""Add weight column to video_vectors.

Revision ID: 003_add_weight
Revises: f69c983981da
Create Date: 2026-06-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_add_weight"
down_revision: str | Sequence[str] | None = "f69c983981da"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "video_vectors",
        sa.Column("weight", sa.Float(), nullable=True, server_default="1.0"),
    )


def downgrade() -> None:
    op.drop_column("video_vectors", "weight")
