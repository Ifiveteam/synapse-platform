from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class UserIdealPersona(TimestampMixin, Base):
    """사용자 확정 이상 자아. [네비게이터]"""

    __tablename__ = "user_ideal_persona"

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

    # 목표 8축 (user_profile_history의 8축과 동일 정의)
    exploration: Mapped[float | None] = mapped_column(Float, nullable=True)
    analytical: Mapped[float | None] = mapped_column(Float, nullable=True)
    creativity: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution: Mapped[float | None] = mapped_column(Float, nullable=True)
    achievement_drive: Mapped[float | None] = mapped_column(Float, nullable=True)
    autonomy: Mapped[float | None] = mapped_column(Float, nullable=True)
    sociality: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensitivity: Mapped[float | None] = mapped_column(Float, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_uip_user", "user_id"),)
