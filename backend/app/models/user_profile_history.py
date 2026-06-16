from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class UserProfileHistory(TimestampMixin, Base):
    """성향 누적 스냅샷 (Core Truth). [프로파일러]"""

    __tablename__ = "user_profile_history"

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
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Schwartz Value (가치관, 10)
    self_direction: Mapped[float | None] = mapped_column(Float, nullable=True)
    stimulation: Mapped[float | None] = mapped_column(Float, nullable=True)
    achievement: Mapped[float | None] = mapped_column(Float, nullable=True)
    power: Mapped[float | None] = mapped_column(Float, nullable=True)
    security: Mapped[float | None] = mapped_column(Float, nullable=True)
    benevolence: Mapped[float | None] = mapped_column(Float, nullable=True)
    universalism: Mapped[float | None] = mapped_column(Float, nullable=True)
    hedonism: Mapped[float | None] = mapped_column(Float, nullable=True)
    conformity: Mapped[float | None] = mapped_column(Float, nullable=True)
    tradition: Mapped[float | None] = mapped_column(Float, nullable=True)

    # TCI (기질)
    novelty_seeking: Mapped[float | None] = mapped_column(Float, nullable=True)
    persistence: Mapped[float | None] = mapped_column(Float, nullable=True)
    self_transcendence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 8축 스파이더 (행동 성향)
    exploration: Mapped[float | None] = mapped_column(Float, nullable=True)
    analytical: Mapped[float | None] = mapped_column(Float, nullable=True)
    creativity: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution: Mapped[float | None] = mapped_column(Float, nullable=True)
    achievement_drive: Mapped[float | None] = mapped_column(Float, nullable=True)
    autonomy: Mapped[float | None] = mapped_column(Float, nullable=True)
    sociality: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensitivity: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_uph_user_date", text("user_id"), text("snapshot_date DESC")),
    )
