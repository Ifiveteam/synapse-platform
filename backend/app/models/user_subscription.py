"""사용자 구독 채널 — Takeout 구독정보.csv 적재 (인덱서)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class UserSubscription(TimestampMixin, Base):
    """Takeout 구독 스냅샷. 채널 단위 1행 — 업로드 시마다 전체 교체."""

    __tablename__ = "user_subscription"

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

    channel_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_title: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_usub_user_channel"),
        Index("ix_usub_user", "user_id"),
    )
