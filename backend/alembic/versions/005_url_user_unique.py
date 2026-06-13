"""Change url unique to (url, user_id) composite unique.

Revision ID: 005_url_user_unique
Revises: 004_add_user_id
Create Date: 2026-06-14

"""

from collections.abc import Sequence

from alembic import op

revision: str = "005_url_user_unique"
down_revision: str | Sequence[str] | None = "004_add_user_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL user_id 고아 데이터 제거
    op.execute("DELETE FROM video_vectors WHERE user_id IS NULL")
    # 기존 url 단독 유니크 제거
    op.drop_constraint("video_vectors_url_key", "video_vectors", type_="unique")
    # (url, user_id) 복합 유니크 추가
    op.create_unique_constraint(
        "video_vectors_url_user_key", "video_vectors", ["url", "user_id"]
    )


def downgrade() -> None:
    op.drop_constraint("video_vectors_url_user_key", "video_vectors", type_="unique")
    op.create_unique_constraint("video_vectors_url_key", "video_vectors", ["url"])
