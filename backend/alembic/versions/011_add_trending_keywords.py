"""add trending_keywords JSONB to global_trends_snapshot

Phase 2-5: 급상승 키워드 NLP 랭킹 적재 컬럼.

Revision ID: 011_add_trending_keywords
Revises: 010_add_aggregator_tables
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "011_add_trending_keywords"
down_revision: str | Sequence[str] | None = "010_add_aggregator_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "global_trends_snapshot",
        sa.Column(
            "trending_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="NLP 명사 추출·7일 이동평균 대비 급상승 키워드 랭킹",
        ),
    )


def downgrade() -> None:
    op.drop_column("global_trends_snapshot", "trending_keywords")
