"""add keyword_context_map and knowledge_graphs table

Phase 3-2: 교차 도메인 지식 그래프 + 에이전트 키워드 맥락 맵.

Revision ID: 012_add_knowledge_graphs
Revises: 011_add_trending_keywords
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "012_add_knowledge_graphs"
down_revision: str | Sequence[str] | None = "011_add_trending_keywords"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "global_trends_snapshot",
        sa.Column(
            "keyword_context_map",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="에이전트 소스별 동시 출현 키워드 맥락·도메인 가중치",
        ),
    )

    op.create_table(
        "knowledge_graphs",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "graph_date",
            sa.Date(),
            nullable=False,
            comment="KST 기준 분석 일자 (일별 UPSERT 키)",
        ),
        sa.Column(
            "snapshot_id",
            sa.UUID(),
            nullable=True,
            comment="원본 GlobalTrendsSnapshot 참조",
        ),
        sa.Column(
            "graph_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment='react-force-graph 표준: {"nodes": [...], "links": [...]}',
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="node_count·link_count·algorithm 등 메타",
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="그래프 생성 완료 시각",
        ),
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
            ["snapshot_id"],
            ["global_trends_snapshot.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("graph_date", name="uq_knowledge_graphs_graph_date"),
    )
    op.create_index(
        "ix_knowledge_graphs_graph_date",
        "knowledge_graphs",
        [sa.literal_column("graph_date DESC")],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_graphs_snapshot_id",
        "knowledge_graphs",
        ["snapshot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_graphs_snapshot_id", table_name="knowledge_graphs")
    op.drop_index("ix_knowledge_graphs_graph_date", table_name="knowledge_graphs")
    op.drop_table("knowledge_graphs")
    op.drop_column("global_trends_snapshot", "keyword_context_map")
