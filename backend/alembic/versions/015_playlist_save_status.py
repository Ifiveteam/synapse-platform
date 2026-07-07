"""navigator_playlist에 save_status(YouTube 저장 상태) 컬럼 추가

재생목록을 실제 YouTube에 비동기로 저장하기 위해 none/saving/saved/failed 상태를 둔다.
기존 행은 none(server_default).

Revision ID: 015_playlist_save_status
Revises: 014_playlist_status
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "015_playlist_save_status"
down_revision: str | Sequence[str] | None = "014_playlist_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "navigator_playlist",
        sa.Column(
            "save_status",
            sa.Text(),
            nullable=False,
            server_default="none",
        ),
    )


def downgrade() -> None:
    op.drop_column("navigator_playlist", "save_status")
