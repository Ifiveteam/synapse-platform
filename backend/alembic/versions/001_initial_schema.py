"""Initial schema (Synapse ERD baseline).

Creates pgvector + pgcrypto extensions and all UUID-keyed tables:
users, user_token, user_video_watch, video_analysis,
user_feature_snapshot, user_profile_history, user_profile_insight,
user_ideal_persona.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1536


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _fk_user(nullable: bool = False, *, ondelete: str = "CASCADE") -> sa.Column:
    return sa.Column(
        "user_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete=ondelete),
        nullable=nullable,
    )


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def _updated_at() -> sa.Column:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 0. users
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("google_sub_id", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("picture", sa.Text()),
        sa.Column("access_token", sa.Text()),
        sa.Column(
            "analysis_interval",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'WEEKLY'"),
        ),
        sa.Column(
            "next_analysis_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        _created_at(),
    )
    op.create_index("ix_users_next_analysis", "users", ["next_analysis_at"])

    # 0-1. user_token (1:1)
    op.create_table(
        "user_token",
        _uuid_pk(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("refresh_token", sa.String(512), nullable=False),
        sa.Column("google_refresh_token", sa.String(512)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        _created_at(),
        _updated_at(),
    )

    # 1. user_video_watch
    op.create_table(
        "user_video_watch",
        _uuid_pk(),
        _fk_user(),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("channel_url", sa.Text()),
        sa.Column("title", sa.Text()),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("watched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration", sa.Integer()),
        sa.Column("is_shorts", sa.Boolean()),
        sa.Column("description", sa.Text()),
        sa.Column("tags", postgresql.JSONB()),
        sa.Column("category", sa.String(50)),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("transcript", sa.Text()),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("user_id", "url", name="uq_uvw_user_url"),
    )
    op.create_index(
        "ix_uvw_user_watched",
        "user_video_watch",
        ["user_id", sa.text("watched_at DESC")],
    )
    op.create_index("ix_uvw_category", "user_video_watch", ["category"])

    # 2. video_analysis (1:1 with user_video_watch)
    op.create_table(
        "video_analysis",
        _uuid_pk(),
        sa.Column(
            "user_video_watch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_video_watch.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("summary_kr", sa.Text()),
        sa.Column("tones", postgresql.JSONB()),
        sa.Column("intents", postgresql.JSONB()),
        sa.Column("value_signals", postgresql.JSONB()),
        sa.Column("embedding_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        _created_at(),
        _updated_at(),
    )
    op.create_index(
        "ix_va_embedding",
        "video_analysis",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # 3. user_feature_snapshot
    op.create_table(
        "user_feature_snapshot",
        _uuid_pk(),
        _fk_user(),
        sa.Column("analysis_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysis_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category_ratio", postgresql.JSONB()),
        sa.Column("video_type_ratio", postgresql.JSONB()),
        sa.Column("channel_top5", postgresql.JSONB()),
        sa.Column("category_top5", postgresql.JSONB()),
        sa.Column("category_channel_diversity", postgresql.JSONB()),
        _created_at(),
        sa.UniqueConstraint(
            "user_id", "analysis_start", "analysis_end", name="uq_ufs_user_period"
        ),
    )
    op.create_index(
        "ix_ufs_user_period",
        "user_feature_snapshot",
        ["user_id", sa.text("analysis_end DESC")],
    )

    # 4. user_profile_history
    op.create_table(
        "user_profile_history",
        _uuid_pk(),
        _fk_user(),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        # Schwartz Value (10)
        sa.Column("self_direction", sa.Float()),
        sa.Column("stimulation", sa.Float()),
        sa.Column("achievement", sa.Float()),
        sa.Column("power", sa.Float()),
        sa.Column("security", sa.Float()),
        sa.Column("benevolence", sa.Float()),
        sa.Column("universalism", sa.Float()),
        sa.Column("hedonism", sa.Float()),
        sa.Column("conformity", sa.Float()),
        sa.Column("tradition", sa.Float()),
        # TCI (3)
        sa.Column("novelty_seeking", sa.Float()),
        sa.Column("persistence", sa.Float()),
        sa.Column("self_transcendence", sa.Float()),
        # 8-axis spider
        sa.Column("exploration", sa.Float()),
        sa.Column("analytical", sa.Float()),
        sa.Column("creativity", sa.Float()),
        sa.Column("execution", sa.Float()),
        sa.Column("achievement_drive", sa.Float()),
        sa.Column("autonomy", sa.Float()),
        sa.Column("sociality", sa.Float()),
        sa.Column("sensitivity", sa.Float()),
        _created_at(),
        _updated_at(),
    )
    op.create_index(
        "ix_uph_user_date",
        "user_profile_history",
        ["user_id", sa.text("snapshot_date DESC")],
    )

    # 5. user_profile_insight
    op.create_table(
        "user_profile_insight",
        _uuid_pk(),
        _fk_user(),
        sa.Column(
            "user_profile_history_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profile_history.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("persona_label", sa.String(100)),
        sa.Column("behavior_reasoning", sa.Text()),
        sa.Column("dominant_traits", postgresql.JSONB()),
        sa.Column("supporting_evidence", postgresql.JSONB()),
        sa.Column("tone_of_user", sa.Text()),
        _created_at(),
    )
    op.create_index(
        "ix_upi_user",
        "user_profile_insight",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_upi_history", "user_profile_insight", ["user_profile_history_id"]
    )

    # 6. user_ideal_persona
    op.create_table(
        "user_ideal_persona",
        _uuid_pk(),
        _fk_user(),
        sa.Column("exploration", sa.Float()),
        sa.Column("analytical", sa.Float()),
        sa.Column("creativity", sa.Float()),
        sa.Column("execution", sa.Float()),
        sa.Column("achievement_drive", sa.Float()),
        sa.Column("autonomy", sa.Float()),
        sa.Column("sociality", sa.Float()),
        sa.Column("sensitivity", sa.Float()),
        sa.Column("description", sa.Text()),
        _created_at(),
        _updated_at(),
    )
    op.create_index("ix_uip_user", "user_ideal_persona", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_ideal_persona")
    op.drop_table("user_profile_insight")
    op.drop_table("user_profile_history")
    op.drop_table("user_feature_snapshot")
    op.drop_table("video_analysis")
    op.drop_table("user_video_watch")
    op.drop_table("user_token")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
    op.execute("DROP EXTENSION IF EXISTS vector")
