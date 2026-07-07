"""batch + source→catalog membership (배치 단위 프로파일 분석)

- analysis_batch: '분석 시작' 클릭 단위 묶음 (seal로 닫고 그 배치로 프로파일 1회)
- analysis_source_catalog: 소스(파일)↔시청영상 다대다 소속 (창고 정본은 그대로)
- user_analysis_source.batch_id / user_profile_history.batch_id 추가

Revision ID: 010_batch_source_catalog
Revises: 009_interval_months
Create Date: 2026-07-02

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010_batch_source_catalog"
down_revision: str | Sequence[str] | None = "009_interval_months"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) 배치 테이블
    op.create_table(
        "analysis_batch",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="open", nullable=False
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ab_user_created",
        "analysis_batch",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )

    # 2) 소스 ↔ catalog 소속 조인 테이블
    op.create_table(
        "analysis_source_catalog",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("analysis_source_id", sa.UUID(), nullable=False),
        sa.Column("catalog_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_source_id"],
            ["user_analysis_source.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_id"], ["user_watch_catalog.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_source_id", "catalog_id", name="uq_asc_source_catalog"
        ),
    )
    op.create_index(
        "ix_asc_source", "analysis_source_catalog", ["analysis_source_id"], unique=False
    )
    op.create_index(
        "ix_asc_catalog", "analysis_source_catalog", ["catalog_id"], unique=False
    )

    # 3) batch_id 컬럼 (소스·스냅샷)
    op.add_column(
        "user_analysis_source", sa.Column("batch_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_uas_batch",
        "user_analysis_source",
        "analysis_batch",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_uas_batch", "user_analysis_source", ["batch_id"], unique=False)

    op.add_column(
        "user_profile_history", sa.Column("batch_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_uph_batch",
        "user_profile_history",
        "analysis_batch",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_uph_batch", "user_profile_history", type_="foreignkey")
    op.drop_column("user_profile_history", "batch_id")

    op.drop_index("ix_uas_batch", table_name="user_analysis_source")
    op.drop_constraint("fk_uas_batch", "user_analysis_source", type_="foreignkey")
    op.drop_column("user_analysis_source", "batch_id")

    op.drop_index("ix_asc_catalog", table_name="analysis_source_catalog")
    op.drop_index("ix_asc_source", table_name="analysis_source_catalog")
    op.drop_table("analysis_source_catalog")

    op.drop_index("ix_ab_user_created", table_name="analysis_batch")
    op.drop_table("analysis_batch")
