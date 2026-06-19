"""Extension auth code table + extension refresh columns on user_token.

Revision ID: 006_extension_auth
Revises: 005_create_ai_chat_logs
Create Date: 2026-06-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_extension_auth"
down_revision: str | None = "005_create_ai_chat_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_token",
        sa.Column("extension_refresh_token", sa.String(512), nullable=True),
    )
    op.add_column(
        "user_token",
        sa.Column("extension_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "extension_auth_code",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index(
        "ix_extension_auth_code_user_id",
        "extension_auth_code",
        ["user_id"],
    )
    op.create_index(
        "ix_extension_auth_code_expires_at",
        "extension_auth_code",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_extension_auth_code_expires_at", "extension_auth_code")
    op.drop_index("ix_extension_auth_code_user_id", "extension_auth_code")
    op.drop_table("extension_auth_code")
    op.drop_column("user_token", "extension_expires_at")
    op.drop_column("user_token", "extension_refresh_token")
