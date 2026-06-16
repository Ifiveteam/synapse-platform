from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class UserFeatureSnapshot(Base):
    """기간 집계 feature. [인덱서]"""

    __tablename__ = "user_feature_snapshot"

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

    analysis_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    analysis_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    category_ratio: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    video_type_ratio: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    channel_top5: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    category_top5: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    category_channel_diversity: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "analysis_start", "analysis_end", name="uq_ufs_user_period"
        ),
        Index("ix_ufs_user_period", text("user_id"), text("analysis_end DESC")),
    )
