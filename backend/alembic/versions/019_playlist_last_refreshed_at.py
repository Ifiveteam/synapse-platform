"""navigator_playlist: 마지막 갱신 시각(last_refreshed_at) 추가

- last_refreshed_at(timestamptz, nullable) — 자동 갱신 스케줄러의 주기 도래 판정용.
  생성·재생성마다 갱신. null이면 아직 미갱신(다음 tick에 대상).

Revision ID: 019_playlist_last_refreshed_at
Revises: 018_playlist_refresh_period
Create Date: 2026-07-06

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "019_playlist_last_refreshed_at"
down_revision: str | Sequence[str] | None = "018_playlist_refresh_period"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "navigator_playlist",
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("navigator_playlist", "last_refreshed_at")
