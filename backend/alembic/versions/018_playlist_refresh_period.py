"""navigator_playlist: 자동 갱신 주기(refresh_period) 추가

- refresh_period(none|daily|weekly|monthly, 기본 none) 컬럼 추가.
  주기 선택 저장·편집용(스케줄러 연동은 별도).

Revision ID: 018_playlist_refresh_period
Revises: 017_ideal_taste_keywords
Create Date: 2026-07-05

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "018_playlist_refresh_period"
down_revision: str | Sequence[str] | None = "017_ideal_taste_keywords"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "navigator_playlist",
        sa.Column(
            "refresh_period",
            sa.Text(),
            server_default=sa.text("'none'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("navigator_playlist", "refresh_period")
