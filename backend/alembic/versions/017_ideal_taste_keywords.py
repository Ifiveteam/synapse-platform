"""user_ideal_persona: 대화에서 뽑은 구체 관심 키워드(taste_keywords) 추가

- taste_keywords(JSONB, nullable) 컬럼 추가 — 재생목록 검색 씨앗용.
  대화로 설계한 이상향만 채워지고, 기존/대화 없는 행은 null.

Revision ID: 017_ideal_taste_keywords
Revises: 016_navigator_proposal_status
Create Date: 2026-07-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "017_ideal_taste_keywords"
down_revision: str | Sequence[str] | None = "016_navigator_proposal_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_ideal_persona",
        sa.Column("taste_keywords", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_ideal_persona", "taste_keywords")
