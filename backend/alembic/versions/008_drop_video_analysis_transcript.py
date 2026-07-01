"""drop video_analysis.transcript column

자막(youtube-transcript-api)은 IP 차단으로 실사용 불가(수집률 0%)라 제거한다.
프로파일러는 제목·설명·태그·카테고리 메타데이터만으로 의미분석한다.

Revision ID: 008_drop_transcript
Revises: 007_user_behavior_logs
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008_drop_transcript"
down_revision: str | Sequence[str] | None = "007_user_behavior_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("video_analysis", "transcript")


def downgrade() -> None:
    op.add_column(
        "video_analysis",
        sa.Column("transcript", sa.Text(), nullable=True),
    )
