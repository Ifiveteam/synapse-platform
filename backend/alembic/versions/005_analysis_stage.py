"""user_analysis_source에 stage 컬럼 추가

분류(indexing) / 분석(profiling) 진행 단계를 표시용으로 기록한다.
status(running/completed/failed)는 그대로 두고, running일 때 세부단계만 표현.

Revision ID: 005_analysis_stage
Revises: 004_drive_folder
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_analysis_stage"
down_revision: str | Sequence[str] | None = "004_drive_folder"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_analysis_source",
        sa.Column(
            "stage",
            sa.String(length=20),
            nullable=False,
            server_default="indexing",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_analysis_source", "stage")
