from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
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

    # 이 이상향이 근거로 삼은 프로필 스냅샷 (21축 추적용)
    source_profile_history_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile_history.id", ondelete="SET NULL"),
        nullable=True,
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

    # 이상향을 한마디로 부르는 페르소나 명칭 (프로파일러 persona_label과 동일 성격)
    persona_label: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 이상향 설계 원본 13축(가치관10+기질3). 8축은 여기서 파생됨. (없으면 레거시)
    values_temperament: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 유저당 여러 이상향 보관, 그중 하나만 "적용 중"
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    # 행동 가이드 캐시 (이상향 + source 스냅샷에 고정, 1안)
    # guide_catalog_count = 생성 당시 시청기록 수 → 현재 수와 다르면 stale 표시
    guide_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    guide_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    guide_catalog_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_uip_user", "user_id"),
        Index("ix_uip_user_active", "user_id", "is_active"),
    )
