from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base

EMBEDDING_DIM = 1536


class VideoVector(Base):
    __tablename__ = "video_vectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str | None] = mapped_column(Text)
    channel_url: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text, unique=True)
    watched_at: Mapped[datetime | None] = mapped_column(DateTime)
    category: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    duration: Mapped[int | None] = mapped_column(Integer)
    is_shorts: Mapped[bool | None] = mapped_column(Boolean)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    weight: Mapped[float | None] = mapped_column(Float, default=1.0)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
