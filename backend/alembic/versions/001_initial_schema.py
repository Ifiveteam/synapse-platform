"""initial schema (squashed baseline)

기존 001~013 + navigator_playlist + watch_count 마이그레이션을 단일 baseline으로 통합한 스키마.
pgvector + pgcrypto 확장과 전체 테이블/인덱스(HNSW 포함)를 생성한다.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-06-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("google_sub_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("picture", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column(
            "plan",
            sa.String(length=20),
            server_default=sa.text("'free'"),
            nullable=False,
        ),
        sa.Column(
            "analysis_interval",
            sa.String(length=50),
            server_default=sa.text("'WEEKLY'"),
            nullable=False,
        ),
        sa.Column(
            "next_analysis_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_sub_id"),
    )
    op.create_index(
        "ix_users_next_analysis", "users", ["next_analysis_at"], unique=False
    )
    op.create_table(
        "ai_chat_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("agent_type", sa.String(length=30), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("context_url", sa.String(length=2048), nullable=True),
        sa.Column("context_title", sa.String(length=512), nullable=True),
        sa.Column("content_embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_chat_logs_agent_type"), "ai_chat_logs", ["agent_type"], unique=False
    )
    op.create_index(
        "ix_ai_chat_logs_content_embedding",
        "ai_chat_logs",
        ["content_embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"content_embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("ix_ai_chat_logs_session_id"), "ai_chat_logs", ["session_id"], unique=False
    )
    op.create_index(
        op.f("ix_ai_chat_logs_user_id"), "ai_chat_logs", ["user_id"], unique=False
    )
    op.create_table(
        "extension_auth_code",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
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
        op.f("ix_extension_auth_code_expires_at"),
        "extension_auth_code",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_extension_auth_code_user_id"),
        "extension_auth_code",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "user_profile_history",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("self_direction", sa.Float(), nullable=True),
        sa.Column("stimulation", sa.Float(), nullable=True),
        sa.Column("achievement", sa.Float(), nullable=True),
        sa.Column("power", sa.Float(), nullable=True),
        sa.Column("security", sa.Float(), nullable=True),
        sa.Column("benevolence", sa.Float(), nullable=True),
        sa.Column("universalism", sa.Float(), nullable=True),
        sa.Column("hedonism", sa.Float(), nullable=True),
        sa.Column("conformity", sa.Float(), nullable=True),
        sa.Column("tradition", sa.Float(), nullable=True),
        sa.Column("novelty_seeking", sa.Float(), nullable=True),
        sa.Column("persistence", sa.Float(), nullable=True),
        sa.Column("self_transcendence", sa.Float(), nullable=True),
        sa.Column("exploration", sa.Float(), nullable=True),
        sa.Column("analytical", sa.Float(), nullable=True),
        sa.Column("creativity", sa.Float(), nullable=True),
        sa.Column("execution", sa.Float(), nullable=True),
        sa.Column("achievement_drive", sa.Float(), nullable=True),
        sa.Column("autonomy", sa.Float(), nullable=True),
        sa.Column("sociality", sa.Float(), nullable=True),
        sa.Column("sensitivity", sa.Float(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("persona_label", sa.String(length=100), nullable=True),
        sa.Column("behavior_reasoning", sa.Text(), nullable=True),
        sa.Column(
            "dominant_traits", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "supporting_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("tone_of_user", sa.Text(), nullable=True),
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
    )
    op.create_index(
        "ix_uph_user_date",
        "user_profile_history",
        [sa.literal_column("user_id"), sa.literal_column("snapshot_date DESC")],
        unique=False,
    )
    op.create_table(
        "user_token",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("refresh_token", sa.String(length=512), nullable=False),
        sa.Column("google_refresh_token", sa.String(length=512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extension_refresh_token", sa.String(length=512), nullable=True),
        sa.Column("extension_expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "user_watch_catalog",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("channel_url", sa.Text(), nullable=True),
        sa.Column("watched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("youtube_category_id", sa.String(length=10), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("is_shorts", sa.Boolean(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("embedding_text", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "watch_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "url", name="uq_uwc_user_url"),
    )
    op.create_index(
        "ix_uwc_embedding",
        "user_watch_catalog",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_uwc_user_category",
        "user_watch_catalog",
        ["user_id", "youtube_category_id"],
        unique=False,
    )
    op.create_index(
        "ix_uwc_user_watched",
        "user_watch_catalog",
        [sa.literal_column("user_id"), sa.literal_column("watched_at DESC")],
        unique=False,
    )
    op.create_table(
        "navigator_proposal_cache",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_profile_history_id", sa.UUID(), nullable=False),
        sa.Column(
            "proposals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("catalog_count", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["source_profile_history_id"],
            ["user_profile_history.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "source_profile_history_id", name="uq_npc_user_snapshot"
        ),
    )
    op.create_table(
        "user_analysis_source",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default="running", nullable=False
        ),
        sa.Column("profile_history_id", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["profile_history_id"], ["user_profile_history.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_key", name="uq_uas_user_source"),
    )
    op.create_index(
        "ix_uas_user_created",
        "user_analysis_source",
        ["user_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_table(
        "user_ideal_persona",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_profile_history_id", sa.UUID(), nullable=True),
        sa.Column("exploration", sa.Float(), nullable=True),
        sa.Column("analytical", sa.Float(), nullable=True),
        sa.Column("creativity", sa.Float(), nullable=True),
        sa.Column("execution", sa.Float(), nullable=True),
        sa.Column("achievement_drive", sa.Float(), nullable=True),
        sa.Column("autonomy", sa.Float(), nullable=True),
        sa.Column("sociality", sa.Float(), nullable=True),
        sa.Column("sensitivity", sa.Float(), nullable=True),
        sa.Column("persona_label", sa.Text(), nullable=True),
        sa.Column(
            "values_temperament", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("guide_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("guide_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("guide_catalog_count", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["source_profile_history_id"],
            ["user_profile_history.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uip_user", "user_ideal_persona", ["user_id"], unique=False)
    op.create_index(
        "ix_uip_user_active",
        "user_ideal_persona",
        ["user_id", "is_active"],
        unique=False,
    )
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
    op.create_table(
        "video_analysis",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("catalog_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("summary_kr", sa.Text(), nullable=False),
        sa.Column("tones", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("intents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "value_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("embedding_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["catalog_id"], ["user_watch_catalog.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_id"),
    )
    op.create_index(
        "ix_va_embedding",
        "video_analysis",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("ix_va_user", "video_analysis", ["user_id"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_np_user_ideal", table_name="navigator_playlist")
    op.drop_table("navigator_playlist")
    op.drop_index("ix_va_user", table_name="video_analysis")
    op.drop_index(
        "ix_va_embedding",
        table_name="video_analysis",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_table("video_analysis")
    op.drop_index("ix_uip_user_active", table_name="user_ideal_persona")
    op.drop_index("ix_uip_user", table_name="user_ideal_persona")
    op.drop_table("user_ideal_persona")
    op.drop_index("ix_uas_user_created", table_name="user_analysis_source")
    op.drop_table("user_analysis_source")
    op.drop_table("navigator_proposal_cache")
    op.drop_index("ix_uwc_user_watched", table_name="user_watch_catalog")
    op.drop_index("ix_uwc_user_category", table_name="user_watch_catalog")
    op.drop_index(
        "ix_uwc_embedding",
        table_name="user_watch_catalog",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_table("user_watch_catalog")
    op.drop_table("user_token")
    op.drop_index("ix_uph_user_date", table_name="user_profile_history")
    op.drop_table("user_profile_history")
    op.drop_index(
        op.f("ix_extension_auth_code_user_id"), table_name="extension_auth_code"
    )
    op.drop_index(
        op.f("ix_extension_auth_code_expires_at"), table_name="extension_auth_code"
    )
    op.drop_table("extension_auth_code")
    op.drop_index(op.f("ix_ai_chat_logs_user_id"), table_name="ai_chat_logs")
    op.drop_index(op.f("ix_ai_chat_logs_session_id"), table_name="ai_chat_logs")
    op.drop_index(
        "ix_ai_chat_logs_content_embedding",
        table_name="ai_chat_logs",
        postgresql_using="hnsw",
        postgresql_ops={"content_embedding": "vector_cosine_ops"},
    )
    op.drop_index(op.f("ix_ai_chat_logs_agent_type"), table_name="ai_chat_logs")
    op.drop_table("ai_chat_logs")
    op.drop_index("ix_users_next_analysis", table_name="users")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
    op.execute("DROP EXTENSION IF EXISTS vector")
