from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class UserProfileHistory(TimestampMixin, Base):
    """성향 점수 + LLM 해석 스냅샷 (시점별). [프로파일러]"""

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

    # LLM 해석
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    behavior_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    dominant_traits: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    supporting_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tone_of_user: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 이 스냅샷을 만든 배치(불변 박제) — 네비게이터가 근거를 배치로 좁힐 때 사용.
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_batch.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 프로파일 초상(portrait): 관심사·성향·소비스타일·키워드·별칭 — 통째로 JSONB
    portrait: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_uph_user_date", text("user_id"), text("snapshot_date DESC")),
    )
