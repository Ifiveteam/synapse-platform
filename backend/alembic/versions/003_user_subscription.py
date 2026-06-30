"""create user_subscription table

Revision ID: 003_user_subscription
Revises: 002_create_scraps
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_user_subscription"
down_revision: str | Sequence[str] | None = "002_create_scraps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_subscription",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("channel_url", sa.Text(), nullable=True),
        sa.Column("channel_title", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("user_id", "channel_id", name="uq_usub_user_channel"),
    )
    op.create_index("ix_usub_user", "user_subscription", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_usub_user", table_name="user_subscription")
    op.drop_table("user_subscription")
