"""navigator_playlist에 status(생성 상태) 컬럼 추가

재생목록을 백그라운드로 비동기 생성하기 위해 pending/ready/failed 상태를 둔다.
기존 행은 ready(server_default).

Revision ID: 014_playlist_status
Revises: 013_ideal_targets
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "014_playlist_status"
down_revision: str | Sequence[str] | None = "013_ideal_targets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "navigator_playlist",
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="ready",
        ),
    )


def downgrade() -> None:
    op.drop_column("navigator_playlist", "status")
