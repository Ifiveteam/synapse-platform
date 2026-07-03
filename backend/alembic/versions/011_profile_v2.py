"""user_profile_history.v2 (V2 실험 프로파일 저장)

관심사 레이더·소비스타일·성향·키워드·별칭을 JSONB 한 컬럼에 저장.
(21축 개별 컬럼은 그대로 — V2는 리스트/가변 구조라 JSONB)

Revision ID: 011_profile_v2
Revises: 010_batch_source_catalog
Create Date: 2026-07-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "011_profile_v2"
down_revision: str | Sequence[str] | None = "010_batch_source_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profile_history",
        sa.Column("v2", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profile_history", "v2")
