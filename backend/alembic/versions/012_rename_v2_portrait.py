"""user_profile_history.v2 → portrait 컬럼 리네임

"v2"는 실험 2세대라는 임시 라벨이었고, 이제 유일한 초상 프로파일이라
내용을 설명하는 이름(portrait)으로 변경. 데이터 변환 없음(컬럼명만).

Revision ID: 012_rename_v2_portrait
Revises: 011_profile_v2
Create Date: 2026-07-02

"""

from collections.abc import Sequence

from alembic import op

revision: str = "012_rename_v2_portrait"
down_revision: str | Sequence[str] | None = "011_profile_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("user_profile_history", "v2", new_column_name="portrait")


def downgrade() -> None:
    op.alter_column("user_profile_history", "portrait", new_column_name="v2")
