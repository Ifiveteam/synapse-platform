from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    google_sub_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    picture: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'free'")
    )

    analysis_interval: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'WEEKLY'")
    )
    # Drive 자동분석 주기(개월). 1~12. 스케줄러가 next_analysis_at 계산에 사용.
    analysis_interval_months: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("2")
    )
    next_analysis_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_users_next_analysis", "next_analysis_at"),)
