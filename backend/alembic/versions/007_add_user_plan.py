"""Add users.plan for subscription tier.

Revision ID: 007_add_user_plan
Revises: 006_extension_auth
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_add_user_plan"
down_revision: str | None = "006_extension_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "plan",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'free'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "plan")
