"""user_ideal_persona에 목표 성향·도메인 컬럼 추가

이상향 설계가 산출하는 목표 성향 6축(target_disposition)과
목표 관심 도메인(target_interest)을 영속한다. 화면 표시(현재→목표)와
재생목록 채널 발굴이 이 값을 읽는다. 기존 행은 NULL(레거시).

Revision ID: 013_ideal_targets
Revises: 012_rename_v2_portrait
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "013_ideal_targets"
down_revision: str | Sequence[str] | None = "012_rename_v2_portrait"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_ideal_persona",
        sa.Column("target_disposition", JSONB(), nullable=True),
    )
    op.add_column(
        "user_ideal_persona",
        sa.Column("target_interest", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_ideal_persona", "target_interest")
    op.drop_column("user_ideal_persona", "target_disposition")
