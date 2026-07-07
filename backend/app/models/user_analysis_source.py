from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class AnalysisSourceStatus:
    PENDING = "pending"  # 큐 대기 중 (유저별 직렬 실행 대기)
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisSourceStage:
    """status=running 동안의 세부 단계 (표시용)."""

    INDEXING = "indexing"  # 분류 중
    INDEXED = "indexed"  # 분류 완료 (배치 분석 대기)
    PROFILING = "profiling"  # 분석 중


class UserAnalysisSource(TimestampMixin, Base):
    """업로드 소스(Takeout 파일) 단위 분석 실행 이력 — 중복 방지."""

    __tablename__ = "user_analysis_source"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=AnalysisSourceStatus.RUNNING,
    )
    stage: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=AnalysisSourceStage.INDEXING,
    )
    profile_history_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_batch.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "source_key", name="uq_uas_user_source"),
        Index("ix_uas_user_created", "user_id", text("created_at DESC")),
        Index("ix_uas_batch", "batch_id"),
    )
