from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class UserToken(TimestampMixin, Base):
    """토큰 관리 (users 1:1)."""

    __tablename__ = "user_token"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    refresh_token: Mapped[str] = mapped_column(String(512), nullable=False)
    google_refresh_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    extension_refresh_token: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    extension_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Takeout 자동 분석용 — 사용자가 Picker로 1회 선택한 Drive 폴더.
    # 스케줄러는 drive_folder_id가 있는 유저만 처리한다(없으면 미연동).
    drive_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drive_folder_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
