"""add users.analysis_interval_months (Drive 자동분석 주기)

Drive 폴더 연동 유저의 자동분석 주기를 1~12개월로 설정 가능하게 한다.
스케줄러가 이 값으로 next_analysis_at을 계산한다.

Revision ID: 009_interval_months
Revises: 008_drop_transcript
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "009_interval_months"
down_revision: str | Sequence[str] | None = "008_drop_transcript"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "analysis_interval_months",
            sa.Integer(),
            nullable=False,
            server_default="2",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "analysis_interval_months")
