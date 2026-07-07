"""어그리게이터 B2B 자동 트렌드 리포트 아카이브."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class B2BReportAudience:
    """리포트 대상 독자 분류."""

    B2B = "B2B"
    GENERAL = "General"


class B2BTrendReport(TimestampMixin, Base):
    """Gemini가 생성한 트렌드 리포트 마크다운 아카이브."""

    __tablename__ = "b2b_trend_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=B2BReportAudience.B2B,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="뉴스레터 발송 완료 시각",
    )

    __table_args__ = (
        Index("ix_b2b_reports_created_at", text("created_at DESC")),
        Index(
            "ix_b2b_reports_published_created",
            "is_published",
            text("created_at DESC"),
        ),
        Index("ix_b2b_reports_target_audience", "target_audience"),
    )
