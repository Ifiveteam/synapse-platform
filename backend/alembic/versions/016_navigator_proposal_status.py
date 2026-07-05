"""navigator_proposal_cache: 비동기 생성 상태(status) 추가

- status(pending|ready|failed) 컬럼 추가 (기존 행은 ready)
- proposals_json / generated_at 를 nullable 로 (pending 행은 결과 없음)

Revision ID: 016_navigator_proposal_status
Revises: 015_playlist_save_status
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "016_navigator_proposal_status"
down_revision: str | Sequence[str] | None = "015_playlist_save_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "navigator_proposal_cache",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="ready",
            nullable=False,
        ),
    )
    op.alter_column(
        "navigator_proposal_cache",
        "proposals_json",
        existing_type=sa.JSON(),
        nullable=True,
    )
    op.alter_column(
        "navigator_proposal_cache",
        "generated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "navigator_proposal_cache",
        "generated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.alter_column(
        "navigator_proposal_cache",
        "proposals_json",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.drop_column("navigator_proposal_cache", "status")
