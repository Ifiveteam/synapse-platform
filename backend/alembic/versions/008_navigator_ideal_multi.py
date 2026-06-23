"""user_ideal_persona: 여러 개 보관 + is_active (Navigator).

Revision ID: 008_navigator_ideal_multi
Revises: 007_navigator_ideal_source
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008_navigator_ideal_multi"
down_revision: str | Sequence[str] | None = "007_navigator_ideal_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_ideal_persona",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_uip_user_active",
        "user_ideal_persona",
        ["user_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_uip_user_active", "user_ideal_persona")
    op.drop_column("user_ideal_persona", "is_active")
