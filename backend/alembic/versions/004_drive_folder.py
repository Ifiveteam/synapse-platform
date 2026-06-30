"""user_token에 Drive 폴더 연동 컬럼 추가

Takeout 자동 분석을 위해 사용자가 Picker로 선택한 Drive 폴더 id/이름을 저장한다.

Revision ID: 004_drive_folder
Revises: 003_user_subscription
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_drive_folder"
down_revision: str | Sequence[str] | None = "003_user_subscription"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_token",
        sa.Column("drive_folder_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user_token",
        sa.Column("drive_folder_name", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_token", "drive_folder_name")
    op.drop_column("user_token", "drive_folder_id")
