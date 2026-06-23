"""users: plan 컬럼 추가 (모델에는 있으나 마이그레이션 누락분 보정).

Revision ID: 013_user_plan
Revises: 012_navigator_proposal_cache
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "013_user_plan"
down_revision: str | Sequence[str] | None = "012_navigator_proposal_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "plan",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'free'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "plan")
