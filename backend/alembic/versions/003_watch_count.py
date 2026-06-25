"""user_watch_catalog.watch_count

분석 윈도우 내 반복 시청 횟수(선호 강도) 보존. 증분 인덱싱과 함께 도입.

Revision ID: 003_watch_count
Revises: 002_navigator_playlist
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_watch_count"
down_revision: str | Sequence[str] | None = "002_navigator_playlist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_watch_catalog",
        sa.Column(
            "watch_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_watch_catalog", "watch_count")
