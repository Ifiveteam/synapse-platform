"""user_ideal_persona: 행동 가이드 캐시 컬럼 (Navigator, 1안).

Revision ID: 009_navigator_guide_cache
Revises: 008_navigator_ideal_multi
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "009_navigator_guide_cache"
down_revision: str | Sequence[str] | None = "008_navigator_ideal_multi"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_ideal_persona",
        sa.Column("guide_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "user_ideal_persona",
        sa.Column(
            "guide_generated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "user_ideal_persona",
        sa.Column("guide_catalog_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_ideal_persona", "guide_catalog_count")
    op.drop_column("user_ideal_persona", "guide_generated_at")
    op.drop_column("user_ideal_persona", "guide_json")
