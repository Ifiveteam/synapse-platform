"""Merge user_profile_insight into user_profile_history.

Revision ID: 003_merge_profile_insight
Revises: 002_move_transcript
Create Date: 2026-06-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003_merge_profile_insight"
down_revision: str | Sequence[str] | None = "002_move_transcript"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profile_history", sa.Column("summary_text", sa.Text(), nullable=True)
    )
    op.add_column(
        "user_profile_history",
        sa.Column("persona_label", sa.String(100), nullable=True),
    )
    op.add_column(
        "user_profile_history",
        sa.Column("behavior_reasoning", sa.Text(), nullable=True),
    )
    op.add_column(
        "user_profile_history",
        sa.Column("dominant_traits", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "user_profile_history",
        sa.Column("supporting_evidence", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "user_profile_history", sa.Column("tone_of_user", sa.Text(), nullable=True)
    )

    op.execute(
        """
        UPDATE user_profile_history h
        SET
            summary_text = i.summary_text,
            persona_label = i.persona_label,
            behavior_reasoning = i.behavior_reasoning,
            dominant_traits = i.dominant_traits,
            supporting_evidence = i.supporting_evidence,
            tone_of_user = i.tone_of_user
        FROM user_profile_insight i
        WHERE i.user_profile_history_id = h.id
        """
    )

    op.drop_index("ix_upi_history", table_name="user_profile_insight")
    op.drop_index("ix_upi_user", table_name="user_profile_insight")
    op.drop_table("user_profile_insight")


def downgrade() -> None:
    op.create_table(
        "user_profile_insight",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_profile_history_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("persona_label", sa.String(100), nullable=True),
        sa.Column("behavior_reasoning", sa.Text(), nullable=True),
        sa.Column("dominant_traits", postgresql.JSONB(), nullable=True),
        sa.Column("supporting_evidence", postgresql.JSONB(), nullable=True),
        sa.Column("tone_of_user", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_profile_history_id"],
            ["user_profile_history.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_upi_user",
        "user_profile_insight",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_upi_history", "user_profile_insight", ["user_profile_history_id"]
    )

    op.execute(
        """
        INSERT INTO user_profile_insight (
            user_id, user_profile_history_id, summary_text, persona_label,
            behavior_reasoning, dominant_traits, supporting_evidence, tone_of_user
        )
        SELECT
            user_id, id, COALESCE(summary_text, ''), persona_label,
            behavior_reasoning, dominant_traits, supporting_evidence, tone_of_user
        FROM user_profile_history
        WHERE summary_text IS NOT NULL
        """
    )

    op.drop_column("user_profile_history", "tone_of_user")
    op.drop_column("user_profile_history", "supporting_evidence")
    op.drop_column("user_profile_history", "dominant_traits")
    op.drop_column("user_profile_history", "behavior_reasoning")
    op.drop_column("user_profile_history", "persona_label")
    op.drop_column("user_profile_history", "summary_text")
