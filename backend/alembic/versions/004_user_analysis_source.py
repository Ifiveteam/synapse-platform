"""Add user_analysis_source for upload deduplication.

Revision ID: 004_user_analysis_source
Revises: 003_merge_profile_insight
Create Date: 2026-06-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004_user_analysis_source"
down_revision: str | Sequence[str] | None = "003_merge_profile_insight"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_analysis_source",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_key", sa.String(512), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default="running",
            nullable=False,
        ),
        sa.Column("profile_history_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["profile_history_id"],
            ["user_profile_history.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_key", name="uq_uas_user_source"),
    )
    op.create_index(
        "ix_uas_user_created",
        "user_analysis_source",
        ["user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_uas_user_created", table_name="user_analysis_source")
    op.drop_table("user_analysis_source")
