"""navigator_playlist table

이상향 기반 YouTube 재생목록 (1 이상향 : N 재생목록).
계획: docs/navigator/PLAN_youtube_playlist.md

Revision ID: 002_navigator_playlist
Revises: 001_initial_schema
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_navigator_playlist"
down_revision: str | Sequence[str] | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "navigator_playlist",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("ideal_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("items_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "channels_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "reservoir_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("youtube_playlist_id", sa.Text(), nullable=True),
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
            ["ideal_id"], ["user_ideal_persona.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_np_user_ideal", "navigator_playlist", ["user_id", "ideal_id"])


def downgrade() -> None:
    op.drop_index("ix_np_user_ideal", table_name="navigator_playlist")
    op.drop_table("navigator_playlist")
