"""user_ideal_persona: 페르소나 명칭 컬럼 (Navigator).

Revision ID: 010_navigator_persona_label
Revises: 009_navigator_guide_cache
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010_navigator_persona_label"
down_revision: str | Sequence[str] | None = "009_navigator_guide_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_ideal_persona",
        sa.Column("persona_label", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_ideal_persona", "persona_label")
