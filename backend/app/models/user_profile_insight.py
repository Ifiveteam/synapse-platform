from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class UserProfileInsight(Base):
    """LLM 성향 해석. [프로파일러]"""

    __tablename__ = "user_profile_insight"

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
    user_profile_history_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile_history.id", ondelete="SET NULL"),
        nullable=True,
    )

    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    persona_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    behavior_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    dominant_traits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    supporting_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tone_of_user: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_upi_user", text("user_id"), text("created_at DESC")),
        Index("ix_upi_history", "user_profile_history_id"),
    )
