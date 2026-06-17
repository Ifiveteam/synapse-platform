"""Create ai_chat_logs table.

Revision ID: 006_create_ai_chat_logs
Revises: 005_url_user_unique
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006_create_ai_chat_logs"
down_revision: str | Sequence[str] | None = "005_url_user_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_chat_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("agent_type", sa.String(length=30), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("context_url", sa.String(length=2048), nullable=True),
        sa.Column("context_title", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_chat_logs_session_id"),
        "ai_chat_logs",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_chat_logs_user_id"),
        "ai_chat_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_chat_logs_agent_type"),
        "ai_chat_logs",
        ["agent_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_chat_logs_agent_type"), table_name="ai_chat_logs")
    op.drop_index(op.f("ix_ai_chat_logs_user_id"), table_name="ai_chat_logs")
    op.drop_index(op.f("ix_ai_chat_logs_session_id"), table_name="ai_chat_logs")
    op.drop_table("ai_chat_logs")
