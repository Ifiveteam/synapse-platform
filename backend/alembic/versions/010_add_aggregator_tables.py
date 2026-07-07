"""add aggregator tables (global_trends_snapshot, b2b_trend_reports)

4 에이전트(어그리게이터) 전용 확장 테이블 및 trend_domain PostgreSQL ENUM 추가.

Revision ID: 010_add_aggregator_tables
Revises: 009_interval_months
Create Date: 2026-07-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "010_add_aggregator_tables"
down_revision: str | Sequence[str] | None = "009_interval_months"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TREND_DOMAIN_ENUM = postgresql.ENUM(
    "Tech/Business",
    "Content/Media",
    "Lifestyle/Wellness",
    "Social/Current Affairs",
    "Knowledge/Education",
    "Economy/TechFin",
    name="trend_domain",
)


def upgrade() -> None:
    TREND_DOMAIN_ENUM.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "global_trends_snapshot",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_date",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="분석 기준 시각 (배치 스냅샷 기준일)",
        ),
        sa.Column(
            "top_domains",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="도메인별 user_count·total_duration·main_category 집계",
        ),
        sa.Column(
            "top_scrap_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="스크랩 내부 카테고리 순위 통계",
        ),
        sa.Column(
            "external_market_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="네이버 데이터랩·구글 RSS 등 외부 시장 키워드 세트",
        ),
        sa.Column(
            "global_8_axis_avg",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment=(
                "2 에이전트 8축 평균: exploration, analytical, creativity, "
                "execution, achievement_drive, autonomy, sociality, sensitivity"
            ),
        ),
        sa.Column(
            "cross_domain_insights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="6대 도메인 교차 분석·LLM 인사이트",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_gts_snapshot_created",
        "global_trends_snapshot",
        [
            sa.literal_column("snapshot_date DESC"),
            sa.literal_column("created_at DESC"),
        ],
        unique=False,
    )

    op.create_table(
        "b2b_trend_reports",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column(
            "target_audience",
            sa.String(length=50),
            server_default="B2B",
            nullable=False,
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "email_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="뉴스레터 발송 완료 시각",
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_b2b_reports_created_at",
        "b2b_trend_reports",
        [sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_b2b_reports_published_created",
        "b2b_trend_reports",
        ["is_published", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_b2b_reports_target_audience",
        "b2b_trend_reports",
        ["target_audience"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_b2b_reports_target_audience", table_name="b2b_trend_reports")
    op.drop_index("ix_b2b_reports_published_created", table_name="b2b_trend_reports")
    op.drop_index("ix_b2b_reports_created_at", table_name="b2b_trend_reports")
    op.drop_table("b2b_trend_reports")

    op.drop_index("ix_gts_snapshot_created", table_name="global_trends_snapshot")
    op.drop_table("global_trends_snapshot")

    TREND_DOMAIN_ENUM.drop(op.get_bind(), checkfirst=True)
