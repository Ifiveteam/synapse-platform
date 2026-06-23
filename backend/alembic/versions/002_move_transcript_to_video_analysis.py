"""Move transcript from user_watch_catalog to video_analysis.

Revision ID: 002_move_transcript
Revises: 001_initial_schema
Create Date: 2026-06-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_move_transcript"
down_revision: str | Sequence[str] | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    va_columns = {col["name"] for col in inspector.get_columns("video_analysis")}
    uwc_columns = {col["name"] for col in inspector.get_columns("user_watch_catalog")}

    # 001_initial_schema may already place transcript on video_analysis.
    if "transcript" not in va_columns:
        op.add_column("video_analysis", sa.Column("transcript", sa.Text(), nullable=True))

    if "transcript" in uwc_columns:
        op.execute(
            """
            UPDATE video_analysis va
            SET transcript = uwc.transcript
            FROM user_watch_catalog uwc
            WHERE va.catalog_id = uwc.id
              AND uwc.transcript IS NOT NULL
              AND va.transcript IS NULL
            """
        )
        op.drop_column("user_watch_catalog", "transcript")


def downgrade() -> None:
    op.add_column(
        "user_watch_catalog", sa.Column("transcript", sa.Text(), nullable=True)
    )
    op.execute(
        """
        UPDATE user_watch_catalog uwc
        SET transcript = va.transcript
        FROM video_analysis va
        WHERE va.catalog_id = uwc.id
          AND va.transcript IS NOT NULL
        """
    )
    op.drop_column("video_analysis", "transcript")
