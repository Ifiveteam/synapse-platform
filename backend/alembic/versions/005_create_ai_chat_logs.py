"""Create ai_chat_logs table (Archiver / Aggregator 통합 채팅 로그).



Revision ID: 005_create_ai_chat_logs

Revises: 004_user_analysis_source

Create Date: 2026-06-18



"""



from collections.abc import Sequence



import sqlalchemy as sa

from pgvector.sqlalchemy import Vector

from sqlalchemy.dialects import postgresql



from alembic import op

from app.core.constants import RAG_EMBEDDING_DIM



revision: str = "005_create_ai_chat_logs"

down_revision: str | Sequence[str] | None = "004_user_analysis_source"

branch_labels: str | Sequence[str] | None = None

depends_on: str | Sequence[str] | None = None



def upgrade() -> None:

    op.create_table(

        "ai_chat_logs",

        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),

        sa.Column("session_id", sa.String(length=50), nullable=False),

        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("agent_type", sa.String(length=30), nullable=False),

        sa.Column("role", sa.String(length=20), nullable=False),

        sa.Column("content", sa.Text(), nullable=False),

        sa.Column("context_url", sa.String(length=2048), nullable=True),

        sa.Column("context_title", sa.String(length=512), nullable=True),

        sa.Column("content_embedding", Vector(RAG_EMBEDDING_DIM), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),

        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),

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

    op.create_index(

        "ix_ai_chat_logs_content_embedding",

        "ai_chat_logs",

        ["content_embedding"],

        unique=False,

        postgresql_using="hnsw",

        postgresql_ops={"content_embedding": "vector_cosine_ops"},

    )





def downgrade() -> None:

    op.drop_index(

        "ix_ai_chat_logs_content_embedding",

        table_name="ai_chat_logs",

        postgresql_using="hnsw",

    )

    op.drop_index(op.f("ix_ai_chat_logs_agent_type"), table_name="ai_chat_logs")

    op.drop_index(op.f("ix_ai_chat_logs_user_id"), table_name="ai_chat_logs")

    op.drop_index(op.f("ix_ai_chat_logs_session_id"), table_name="ai_chat_logs")

    op.drop_table("ai_chat_logs")

