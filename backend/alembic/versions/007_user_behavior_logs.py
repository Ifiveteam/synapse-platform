"""create user_behavior_logs table

Revision ID: 007_user_behavior_logs
Revises: 006_merge_heads
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007_user_behavior_logs"
down_revision: str | Sequence[str] | None = "006_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_behavior_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("page_title", sa.String(length=500), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_behavior_logs_domain"),
        "user_behavior_logs",
        ["domain"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_behavior_logs_id"),
        "user_behavior_logs",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_behavior_logs_timestamp"),
        "user_behavior_logs",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_behavior_logs_user_id"),
        "user_behavior_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_behavior_logs_user_timestamp",
        "user_behavior_logs",
        ["user_id", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_behavior_logs_user_timestamp", table_name="user_behavior_logs"
    )
    op.drop_index(
        op.f("ix_user_behavior_logs_user_id"), table_name="user_behavior_logs"
    )
    op.drop_index(
        op.f("ix_user_behavior_logs_timestamp"), table_name="user_behavior_logs"
    )
    op.drop_index(op.f("ix_user_behavior_logs_id"), table_name="user_behavior_logs")
    op.drop_index(op.f("ix_user_behavior_logs_domain"), table_name="user_behavior_logs")
    op.drop_table("user_behavior_logs")
